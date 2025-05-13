"""
Google Docs utility for interacting with the Google Docs API.

This module provides the GoogleDocsUtils class for fetching and processing Google Documents.
"""

import concurrent.futures
import logging
import os
import socket
from functools import lru_cache
from typing import Any, Dict, List, Optional

from cellmage.config import settings
from cellmage.utils.date_utils import parse_date_input

try:
    import pickle

    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    _GDOCS_AVAILABLE = True
except ImportError:
    _GDOCS_AVAILABLE = False

    # Define placeholder types for type checking when google packages are not available
    class service_account:
        class Credentials:
            pass

    class Credentials:
        pass

    class InstalledAppFlow:
        pass

    def build(*args, **kwargs):
        return None

    class Request:
        pass

    import pickle  # Still try to import pickle as it's a standard library


# --- Setup Logging ---
logger = logging.getLogger(__name__)


def find_first_existing_path(path_list_str: str) -> Optional[str]:
    """
    Given a string of colon-separated paths, return the first one that exists.

    Args:
        path_list_str: Colon-separated string of file paths to check

    Returns:
        The first existing path, or None if none exist
    """
    if not path_list_str:
        return None

    paths = [p.strip() for p in path_list_str.split(":")]
    for path in paths:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            return expanded_path

    # If no path exists, return the first path (will be created if necessary)
    return os.path.expanduser(paths[0])


# Helper function to make arguments hashable for LRU cache (reused from other utils)
def _make_hashable(arg: Any) -> Any:
    """Make an argument hashable for LRU cache."""
    if isinstance(arg, list):
        try:
            return tuple(sorted(arg))
        except TypeError:
            return tuple(arg)
    if isinstance(arg, set):
        return tuple(sorted(list(arg)))
    if isinstance(arg, dict):
        return tuple(sorted(arg.items()))
    return arg


# Custom cache decorator (reused from other utils)
def hashable_lru_cache(maxsize=128, typed=False):
    """LRU cache decorator that can handle unhashable arguments."""

    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize, typed=typed)(func)

        def wrapper(*args, **kwargs):
            hashable_args = tuple(_make_hashable(arg) for arg in args)
            hashable_kwargs = {k: _make_hashable(v) for k, v in kwargs.items()}
            return cached_func(*hashable_args, **hashable_kwargs)

        wrapper.cache_info = cached_func.cache_info
        wrapper.cache_clear = cached_func.cache_clear
        return wrapper

    return decorator


class GoogleDocsUtils:
    """
    Utility class for interacting with the Google Docs API.

    Fetches and processes Google Documents, preparing data for analysis or LLM input.
    """

    _gdoc_service: Optional[Any] = None
    _drive_service: Optional[Any] = None

    def __init__(
        self,
        auth_type: Optional[str] = None,
        token_path: Optional[str] = None,
        credentials_path: Optional[str] = None,
        service_account_path: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize GoogleDocsUtils.

        Args:
            auth_type: Type of authentication to use ('oauth' or 'service_account').
                Defaults to the value in CellMage config.
            token_path: Path to token pickle file for OAuth 2.0 authentication.
                If not provided, will check locations from CellMage config.
            credentials_path: Path to client credentials JSON file for OAuth 2.0 authentication.
                If not provided, will check locations from CellMage config.
            service_account_path: Path to service account JSON file.
                If not provided, will check locations from CellMage config.
            scopes: OAuth 2.0 scopes.
                Defaults to the value in CellMage config.
            timeout: Request timeout in seconds.
                If None, uses the value from settings.gdocs_request_timeout (default: 300).

        Raises:
            ImportError: If required Google API modules are not installed.
            ValueError: If authentication fails or required files are missing.
        """
        if not _GDOCS_AVAILABLE:
            raise ImportError(
                "The Google API packages are required but not installed. "
                "Please install with 'pip install cellmage[gdocs]'."
            )

        # Try to load from .env using dotenv if available
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass  # Continue without dotenv

        self.auth_type = auth_type.lower() if auth_type else settings.gdocs_auth_type
        self.timeout = timeout if timeout is not None else settings.gdocs_request_timeout

        # Find the first existing path, or use the first path in the list if none exist
        self.token_path = token_path or find_first_existing_path(settings.gdocs_token_path)
        self.credentials_path = credentials_path or find_first_existing_path(
            settings.gdocs_credentials_path
        )
        self.service_account_path = service_account_path or find_first_existing_path(
            settings.gdocs_service_account_path
        )

        self.scopes = scopes or settings.gdocs_scopes

        # Make dirs if they don't exist and the directory name is not empty
        if self.token_path:
            token_dir = os.path.dirname(self.token_path)
            if token_dir:  # Only create directory if there's a directory name
                os.makedirs(token_dir, exist_ok=True)

        # Service is initialized lazily via the 'service' property
        logger.info(
            f"GoogleDocsUtils initialized with auth_type: {self.auth_type}, timeout: {self.timeout}s"
        )

    def _get_credentials(self) -> Credentials:
        """Get Google API credentials based on the auth_type."""
        creds = None

        if self.auth_type == "service_account":
            if not self.service_account_path or not os.path.exists(self.service_account_path):
                raise ValueError(
                    "Service account JSON file not found. "
                    "Set CELLMAGE_GDOCS_SERVICE_ACCOUNT_PATH or provide service_account_path parameter."
                )
            try:
                creds = service_account.Credentials.from_service_account_file(
                    self.service_account_path, scopes=self.scopes
                )
                logger.info(f"Authenticated using service account from {self.service_account_path}")
                return creds
            except Exception as e:
                logger.error(f"Error loading service account credentials: {e}", exc_info=True)
                raise ValueError(f"Failed to load service account credentials: {str(e)}")

        # Default to OAuth flow
        if self.token_path and os.path.exists(self.token_path):
            try:
                with open(self.token_path, "rb") as token:
                    creds = pickle.load(token)
                    logger.info(f"Loaded credentials from token file: {self.token_path}")
            except Exception as e:
                logger.warning(f"Error loading token file: {e}", exc_info=False)
                creds = None

        # Check if credentials need refreshing or are missing
        if not creds or not creds.valid:
            if (
                creds
                and hasattr(creds, "expired")
                and creds.expired
                and hasattr(creds, "refresh_token")
                and creds.refresh_token
            ):
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired credentials.")
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}", exc_info=False)
                    creds = None
            else:
                if not self.credentials_path or not os.path.exists(self.credentials_path):
                    paths_list = settings.gdocs_credentials_path.replace(":", "\n- ")
                    raise ValueError(
                        "OAuth credentials file not found. "
                        "Set CELLMAGE_GDOCS_CREDENTIALS_PATH or provide credentials_path parameter.\n"
                        "Expected locations checked:\n"
                        f"- {paths_list}"
                    )
                try:
                    logger.info(
                        f"Starting OAuth flow with credentials file: {self.credentials_path}"
                    )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.scopes
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("Obtained new credentials through OAuth flow.")
                except Exception as e:
                    logger.error(f"OAuth flow failed: {e}", exc_info=True)
                    raise ValueError(f"Failed during OAuth authentication flow: {str(e)}")

            # Save the credentials for future use
            try:
                # Create token directory if it doesn't exist
                token_dir = os.path.dirname(self.token_path)
                if token_dir:  # Only create directory if there's a directory name
                    os.makedirs(token_dir, exist_ok=True)

                with open(self.token_path, "wb") as token:
                    pickle.dump(creds, token)
                logger.info(f"Saved credentials to {self.token_path}")
            except Exception as e:
                logger.warning(f"Failed to save credentials: {e}", exc_info=False)

        return creds

    @property
    def gdoc_service(self):
        """Lazy-initialized Google Docs API service."""
        if self._gdoc_service is None:
            try:
                logger.info("Initializing Google Docs API service...")
                creds = self._get_credentials()

                # Set global socket timeout
                import socket

                socket.setdefaulttimeout(self.timeout)

                # Build the service without http or client_options timeout parameter
                from googleapiclient.discovery import build

                self._gdoc_service = build("docs", "v1", credentials=creds)
                logger.info("Google Docs API service initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Google Docs API service: {e}", exc_info=True)
                raise RuntimeError(f"Failed to initialize Google Docs API service: {str(e)}")
        return self._gdoc_service

    @property
    def drive_service(self):
        """Lazy-initialized Google Drive API service."""
        if self._drive_service is None:
            try:
                logger.info("Initializing Google Drive API service...")
                creds = self._get_credentials()

                # Set global socket timeout
                import socket

                socket.setdefaulttimeout(self.timeout)

                # Build the service without http or client_options timeout parameter
                from googleapiclient.discovery import build

                self._drive_service = build("drive", "v3", credentials=creds)
                logger.info("Google Drive API service initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Google Drive API service: {e}", exc_info=True)
                raise RuntimeError(f"Failed to initialize Google Drive API service: {str(e)}")
        return self._drive_service

    @hashable_lru_cache(maxsize=64, typed=False)
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Fetch a Google Document by ID (cached).

        Args:
            document_id: The Google Docs document ID.

        Returns:
            Dict containing the document structure.

        Raises:
            RuntimeError: If the document cannot be fetched.
        """
        logger.info(f"Fetching Google Doc with ID: {document_id}")
        try:
            # Get the document content
            document = self.gdoc_service.documents().get(documentId=document_id).execute()
            logger.info(f"Successfully fetched document: {document.get('title', 'Untitled')}")
            return document
        except Exception as e:
            logger.error(f"Error fetching document {document_id}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to fetch document {document_id}: {str(e)}")

    def extract_document_id_from_url(self, url: str) -> str:
        """Extract document ID from a Google Docs URL.

        Args:
            url: Google Docs URL (e.g., https://docs.google.com/document/d/DOC_ID/edit)

        Returns:
            The document ID.

        Raises:
            ValueError: If the URL is not a valid Google Docs URL.
        """
        url = url.strip()

        # Pattern 1: docs.google.com/document/d/{id}/edit
        if "/document/d/" in url:
            parts = url.split("/document/d/")
            if len(parts) < 2:
                raise ValueError(f"Invalid Google Docs URL format: {url}")
            doc_id_part = parts[1]
            # Extract ID (everything before /edit or other parameters)
            doc_id = doc_id_part.split("/")[0].split("?")[0]
            return doc_id

        # Pattern 2: docs.google.com/document/d/{id}
        # Pattern 3: docs.google.com/document/{id}/edit
        # Pattern 4: Directly provided document ID

        if url.startswith("https://docs.google.com/") or url.startswith("http://docs.google.com/"):
            raise ValueError(
                f"Unrecognized Google Docs URL format: {url}\n"
                "Expected format: https://docs.google.com/document/d/DOC_ID/edit"
            )

        # Assume the provided string is a document ID if it's not a URL
        return url

    def extract_text_from_document(self, document: Dict[str, Any]) -> str:
        """Extract plain text content from a Google Document structure.

        Args:
            document: The document structure from the API.

        Returns:
            Plain text content of the document with Markdown formatting.
        """
        text = []

        # We don't add the title here anymore as it will be added in format_document_for_llm
        # to avoid duplication

        # Process document body
        if "body" in document and "content" in document["body"]:
            for element in document["body"]["content"]:
                if "paragraph" in element:
                    paragraph = element["paragraph"]

                    # Handle paragraph formatting based on namedStyleType
                    style_type = paragraph.get("paragraphStyle", {}).get(
                        "namedStyleType", "NORMAL_TEXT"
                    )

                    # Check if this is a list item
                    if "bullet" in paragraph:
                        # Get list info
                        list_id = paragraph["bullet"].get("listId", "")
                        nesting_level = paragraph["bullet"].get("nestingLevel", 0)

                        # Extract text with formatting
                        paragraph_text = []
                        for para_element in paragraph.get("elements", []):
                            processed_text = self._process_paragraph_element(para_element)
                            if processed_text:
                                paragraph_text.append(processed_text)

                        # Combine text and add appropriate list marker
                        if paragraph_text:
                            indent = "  " * nesting_level
                            list_marker = "-"  # Default to unordered list

                            # Check if this is an ordered list
                            list_info = document.get("lists", {}).get(list_id, {})
                            list_properties = list_info.get("listProperties", {})
                            nested_properties = list_properties.get("nestingLevels", [{}])[
                                min(
                                    nesting_level,
                                    len(list_properties.get("nestingLevels", [{}])) - 1,
                                )
                            ]

                            if nested_properties.get("glyphType") == "DECIMAL":
                                list_marker = "1."  # Use 1. for all items - Markdown will render the correct numbers

                            text.append(f"{indent}{list_marker} {''.join(paragraph_text)}")
                    else:
                        # Regular paragraph (non-list)
                        if style_type.startswith("HEADING"):
                            # Convert headings to appropriate Markdown headers
                            heading_level = int(style_type.split("_")[1])
                            # Limit heading level to a max of 6 (Markdown standard)
                            heading_prefix = "#" * min(heading_level, 6) + " "
                        else:
                            heading_prefix = ""

                        # Extract text with formatting
                        paragraph_text = []
                        for para_element in paragraph.get("elements", []):
                            processed_text = self._process_paragraph_element(para_element)
                            if processed_text:
                                paragraph_text.append(processed_text)

                        if paragraph_text:
                            text.append(f"{heading_prefix}{''.join(paragraph_text)}")

                # Handle tables (with improved formatting)
                elif "table" in element:
                    # Check if we need to add a line break if tables come right after other content
                    if text and not text[-1].endswith("\n"):
                        text.append("")

                    for row in element["table"].get("tableRows", []):
                        row_texts = []
                        for cell in row.get("tableCells", []):
                            cell_text = []
                            for cell_content in cell.get("content", []):
                                if "paragraph" in cell_content:
                                    para_texts = []
                                    for cell_para in cell_content["paragraph"].get("elements", []):
                                        processed_text = self._process_paragraph_element(cell_para)
                                        if processed_text:
                                            para_texts.append(processed_text)
                                    if para_texts:
                                        cell_text.append("".join(para_texts))
                            row_texts.append(" ".join(cell_text).strip())

                        if row_texts:
                            text.append("| " + " | ".join(row_texts) + " |")

        return "\n".join(text)

    def _process_paragraph_element(self, element: Dict[str, Any]) -> Optional[str]:
        """Process a paragraph element and convert it to Markdown with appropriate formatting.

        Args:
            element: A paragraph element from the Google Docs API

        Returns:
            Formatted text in Markdown, or None if the element couldn't be processed
        """
        if "textRun" in element:
            content = element["textRun"].get("content", "")
            text_style = element["textRun"].get("textStyle", {})
            return self._apply_text_formatting(content, text_style)

        # Process person mentions (People chips / @mentions)
        elif "person" in element:
            # Extract from the person element (this is the correct structure for @mentions)
            person = element.get("person", {})
            person_properties = person.get("personProperties", {})

            person_name = person_properties.get("name", "Unknown")
            person_email = person_properties.get("email", "")

            mention_text = f"@{person_name}"
            if person_email:
                mention_text = f"{mention_text} ({person_email})"

            return mention_text

        # Process other special elements like equations, footnotes, etc.
        elif "horizontalRule" in element:
            return "\n---\n"
        elif "footnoteReference" in element:
            return f"[^{element.get('footnoteReference', {}).get('footnoteId', '')}]"
        elif "pageBreak" in element:
            return "\n\n[Page Break]\n\n"
        elif "inlineObjectElement" in element:
            # Could be an image or other embedded object
            return "[Embedded Object]"

        return None

    def _apply_text_formatting(self, content: str, text_style: Dict[str, Any]) -> str:
        """Apply text formatting (bold, italic, etc.) to content.

        Args:
            content: The text content to format
            text_style: The style dictionary from the Google Docs API

        Returns:
            Formatted text in Markdown
        """
        if not content:
            return content

        # Strip trailing newlines but preserve them to add back later
        trailing_newlines = ""
        while content.endswith("\n"):
            trailing_newlines += "\n"
            content = content[:-1]

        # Handle hyperlinks - this needs to be done before other formatting
        if text_style.get("link") and text_style["link"].get("url"):
            url = text_style["link"]["url"]
            # Format as Markdown link
            content = f"[{content}]({url})"

        # Apply text formatting - after links are handled
        if text_style.get("bold"):
            content = f"**{content}**"

        if text_style.get("italic"):
            content = f"*{content}*"

        if text_style.get("underline"):
            content = f"__{content}__"

        if text_style.get("strikethrough"):
            content = f"~~{content}~~"

        # Add back trailing newlines
        content += trailing_newlines

        return content

    def format_document_for_llm(self, document_id: str) -> str:
        """Fetch a Google Document by ID and format it for LLM input.

        Args:
            document_id: The Google Docs document ID.

        Returns:
            Formatted document content as Markdown text.
        """
        logger.info(f"Formatting document {document_id} for LLM")
        try:
            document = self.get_document(document_id)
            content = self.extract_text_from_document(document)

            # Add metadata
            metadata = []
            metadata.append(f"# {document.get('title', 'Untitled Document')}")
            metadata.append(f"Document ID: {document_id}")
            metadata.append(f"URL: https://docs.google.com/document/d/{document_id}/edit")
            if "lastModifyingUser" in document:
                user = document["lastModifyingUser"]
                name = user.get("displayName", "Unknown User")
                metadata.append(f"Last modified by: {name}")

            # Add last modified date if available
            if "modifiedTime" in document:
                metadata.append(f"Last modified: {document.get('modifiedTime')}")

            # Format the final content
            formatted_content = "\n".join(metadata) + "\n\n" + content

            logger.info("Successfully formatted document for LLM")
            return formatted_content

        except Exception as e:
            logger.error(f"Error formatting document {document_id} for LLM: {e}", exc_info=True)
            error_message = f"# Error Fetching Google Doc\n\nFailed to fetch or format document {document_id}: {str(e)}"
            return error_message

    def _fetch_document_with_timeout(self, document_id: str, timeout: int) -> str:
        """Helper method to fetch a document with timeout.

        Args:
            document_id: The Google Docs document ID.
            timeout: Timeout in seconds for the fetch operation.

        Returns:
            Formatted document content as Markdown text.

        Raises:
            TimeoutError: If the operation times out.
            Exception: For any other errors during fetching.
        """
        # The socket timeout is set at the instance level, so we just call the format method
        try:
            return self.format_document_for_llm(document_id)
        except Exception as e:
            logger.error(
                f"Error in _fetch_document_with_timeout for doc {document_id}: {e}", exc_info=True
            )
            raise

    def search_documents(
        self,
        search_query: str = "",
        max_results: int = 10,
        author: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        modified_after: Optional[str] = None,
        modified_before: Optional[str] = None,
        order_by: str = "relevance",
    ) -> List[Dict[str, Any]]:
        """Search for Google Docs files matching the given criteria.

        Args:
            search_query: The search term to look for in document titles and content.
            max_results: Maximum number of results to return (default: 10).
            author: Filter by document author/owner (comma or space-separated for multiple authors).
            created_after: Filter by creation date (format: YYYY-MM-DD or natural language like '3 days ago').
            created_before: Filter by creation date (format: YYYY-MM-DD or natural language).
            modified_after: Filter by last modified date (format: YYYY-MM-DD or natural language).
            modified_before: Filter by last modified date (format: YYYY-MM-DD or natural language).
            order_by: How to order results ('relevance', 'modifiedTime', 'createdTime', 'name').

        Returns:
            A list of documents, each as a dict with document metadata.

        Raises:
            RuntimeError: If the search fails.
        """
        logger.info(
            f"Searching for Google Docs documents matching criteria. Query: '{search_query}'"
        )
        try:
            # Start with the base query for Google Docs
            query_parts = ["mimeType='application/vnd.google-apps.document'"]

            # Add search term if provided
            if search_query:
                query_parts.append(
                    f"(name contains '{search_query}' or fullText contains '{search_query}')"
                )

            # Filter by author(s) if provided
            if author:
                # Handle multiple authors (comma or space separated)
                authors = [a.strip() for a in author.replace(",", " ").split() if a.strip()]
                if authors:
                    if len(authors) == 1:
                        query_parts.append(f"'{authors[0]}' in owners")
                    else:
                        # For multiple authors, use OR condition
                        author_conditions = [f"'{a}' in owners" for a in authors]
                        query_parts.append(f"({' or '.join(author_conditions)})")

            # Parse and filter by dates if provided (support natural language dates)
            if created_after:
                parsed_date = parse_date_input(created_after)
                if parsed_date:
                    query_parts.append(f"createdTime > '{parsed_date}T00:00:00'")

            if created_before:
                parsed_date = parse_date_input(created_before)
                if parsed_date:
                    query_parts.append(f"createdTime < '{parsed_date}T23:59:59'")

            if modified_after:
                parsed_date = parse_date_input(modified_after)
                if parsed_date:
                    query_parts.append(f"modifiedTime > '{parsed_date}T00:00:00'")

            if modified_before:
                parsed_date = parse_date_input(modified_before)
                if parsed_date:
                    query_parts.append(f"modifiedTime < '{parsed_date}T23:59:59'")

            # Combine all query parts
            query = " and ".join(query_parts)

            # Determine sort order
            order_param = None
            if order_by == "modifiedTime":
                order_param = "modifiedTime desc"  # Most recently modified first
            elif order_by == "createdTime":
                order_param = "createdTime desc"  # Most recently created first
            elif order_by == "name":
                order_param = "name"  # Alphabetical by name
            # No sort parameter needed for 'relevance' - it's the default

            # Fields to fetch - include creation time, modification time, and owners
            fields = "files(id, name, webViewLink, createdTime, modifiedTime, owners)"

            # Make the API call
            results = (
                self.drive_service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields=fields,
                    pageSize=max_results,
                    orderBy=order_param,
                )
                .execute()
            )

            documents = []
            files = results.get("files", [])

            for file in files:
                # Extract owner information if available
                owners = file.get("owners", [])
                owner_info = owners[0] if owners else {"displayName": "Unknown"}

                doc = {
                    "id": file.get("id"),
                    "name": file.get("name", "Untitled"),
                    "url": file.get(
                        "webViewLink", f"https://docs.google.com/document/d/{file.get('id')}/edit"
                    ),
                    "createdTime": file.get("createdTime"),
                    "modifiedTime": file.get("modifiedTime"),
                    "owner": owner_info.get("displayName", "Unknown"),
                    "owners": file.get("owners", []),
                }
                documents.append(doc)

            logger.info(f"Found {len(documents)} Google Docs documents matching the criteria")
            return documents

        except Exception as e:
            logger.error(f"Error searching for documents: {e}", exc_info=True)
            raise RuntimeError(f"Failed to search for documents: {str(e)}")

    def fetch_documents_content_parallel(
        self,
        documents: List[Dict[str, str]],
        max_docs: Optional[int] = None,
        doc_timeout: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Fetch content from multiple documents in parallel.

        Args:
            documents: List of document dicts with 'id', 'name', and 'url' keys.
            max_docs: Maximum number of documents to fetch content for.
                      If None, uses the value from settings.gdocs_parallel_fetch_limit (default: 10).
            doc_timeout: Timeout in seconds for each individual document fetch.
                      If None, uses the value from settings.gdocs_doc_fetch_timeout (default: 60).

        Returns:
            A list of documents with added 'content' key containing the formatted document content.
        """
        # Use the config setting if max_docs or doc_timeout is not provided
        if max_docs is None:
            max_docs = settings.gdocs_parallel_fetch_limit
            logger.info(f"Using configured parallel fetch limit: {max_docs}")

        if doc_timeout is None:
            doc_timeout = settings.gdocs_doc_fetch_timeout
            logger.info(f"Using configured document fetch timeout: {doc_timeout} seconds")

        # Safety check to ensure we're not exceeding a reasonable limit
        max_docs = min(max_docs, len(documents))
        logger.info(f"Fetching content from {max_docs} documents in parallel")

        # Limit to max_docs
        docs_to_fetch = documents[:max_docs]
        result_docs = []

        # Set global socket timeout as a safeguard
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(doc_timeout)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_docs) as executor:
                # Create a future for each document with proper cancellation handling
                future_to_doc = {
                    executor.submit(self._fetch_document_with_timeout, doc["id"], doc_timeout): doc
                    for doc in docs_to_fetch
                }

                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_doc):
                    doc = future_to_doc[future]
                    try:
                        # Get the result with timeout
                        content = future.result(
                            timeout=doc_timeout + 5
                        )  # Extra buffer for future.result() itself
                        doc_with_content = doc.copy()
                        doc_with_content["content"] = content
                        result_docs.append(doc_with_content)
                        logger.info(f"Successfully fetched content for document: {doc['name']}")
                    except concurrent.futures.TimeoutError:
                        logger.error(
                            f"Timeout fetching content for document {doc['id']} after {doc_timeout} seconds"
                        )
                        # Add the document with a timeout error message
                        doc_with_error = doc.copy()
                        doc_with_error["content"] = (
                            f"# Error Fetching Document\n\nTimeout: Failed to fetch content for document '{doc['name']}' "
                            f"within {doc_timeout} seconds. The document may be too large or the server may be slow to respond."
                        )
                        result_docs.append(doc_with_error)
                        # Cancel the future if possible
                        future.cancel()
                    except Exception as e:
                        logger.error(
                            f"Error fetching content for document {doc['id']}: {e}", exc_info=True
                        )
                        # Add the document with an error message
                        doc_with_error = doc.copy()
                        doc_with_error["content"] = (
                            f"# Error Fetching Document\n\nFailed to fetch content for document '{doc['name']}': {str(e)}"
                        )
                        result_docs.append(doc_with_error)
        finally:
            # Restore original socket timeout
            socket.setdefaulttimeout(original_timeout)

        logger.info(f"Completed fetching content for {len(result_docs)} documents")
        return result_docs

    def format_documents_for_llm(self, documents_with_content: List[Dict[str, str]]) -> str:
        """Format multiple documents with content into a single markdown string for LLM.

        Args:
            documents_with_content: List of document dicts with 'content' key.

        Returns:
            A formatted markdown string containing all documents content.
        """
        result = ["# Google Docs Search Results\n"]

        for i, doc in enumerate(documents_with_content, 1):
            result.append(f"## Google Document {i}: {doc['name']}")
            result.append(f"Document ID: {doc['id']}")
            result.append(f"URL: {doc['url']}\n")

            # Add the document content (already formatted as markdown)
            result.append(doc["content"])

            # Add separator between documents except for the last one
            if i < len(documents_with_content):
                result.append("\n---\n")

        return "\n".join(result)

    def close(self) -> None:
        """Close the Google Docs API service resources."""
        if self._gdoc_service:
            logger.info("Closing Google Docs API service.")
            self._gdoc_service = None
            logger.info("Google Docs API service closed.")
        else:
            logger.debug("Google Docs API service was never initialized.")

        if self._drive_service:
            logger.info("Closing Google Drive API service.")
            self._drive_service = None
            logger.info("Google Drive API service closed.")
        else:
            logger.debug("Google Drive API service was never initialized.")

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point. Ensures resources are closed."""
        self.close()
