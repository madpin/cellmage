"""
Google Docs utility for interacting with the Google Docs API.

This module provides the GoogleDocsUtils class for fetching and processing Google Documents.
"""

import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from ..config import settings

# Flag to check if Google API modules are available
_GDOCS_AVAILABLE = False

try:
    import pickle

    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    _GDOCS_AVAILABLE = True
except ImportError:
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

    _service: Optional[Any] = None

    def __init__(
        self,
        auth_type: str = None,
        token_path: Optional[str] = None,
        credentials_path: Optional[str] = None,
        service_account_path: Optional[str] = None,
        scopes: Optional[List[str]] = None,
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
        logger.info(f"GoogleDocsUtils initialized with auth_type: {self.auth_type}")

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
    def service(self):
        """Lazy-initialized Google Docs API service."""
        if self._service is None:
            try:
                logger.info("Initializing Google Docs API service...")
                creds = self._get_credentials()
                self._service = build("docs", "v1", credentials=creds)
                logger.info("Google Docs API service initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Google Docs API service: {e}", exc_info=True)
                raise RuntimeError(f"Failed to initialize Google Docs API service: {str(e)}")
        return self._service

    @hashable_lru_cache(maxsize=64)
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
            document = self.service.documents().get(documentId=document_id).execute()
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
            Plain text content of the document.
        """
        text = []

        # Add document title
        title = document.get("title", "Untitled Document")
        text.append(f"# {title}\n")

        # Process document body
        if "body" in document and "content" in document["body"]:
            for element in document["body"]["content"]:
                if "paragraph" in element:
                    paragraph_text = []
                    for para_element in element["paragraph"].get("elements", []):
                        if "textRun" in para_element:
                            paragraph_text.append(para_element["textRun"].get("content", ""))
                    if paragraph_text:
                        text.append("".join(paragraph_text))

                # Handle tables (simplified - just extract text)
                elif "table" in element:
                    for row in element["table"].get("tableRows", []):
                        row_texts = []
                        for cell in row.get("tableCells", []):
                            cell_text = []
                            for cell_content in cell.get("content", []):
                                if "paragraph" in cell_content:
                                    for cell_para in cell_content["paragraph"].get("elements", []):
                                        if "textRun" in cell_para:
                                            cell_text.append(
                                                cell_para["textRun"].get("content", "")
                                            )
                            row_texts.append("".join(cell_text).strip())
                        if row_texts:
                            text.append(" | ".join(row_texts))

                # Handle lists (simplified extraction)
                elif "list" in element:
                    # Lists are complex in the API - this is simplified
                    text.append("- List item (simplified extraction)")

        return "\n".join(text)

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

            # Format the final content
            formatted_content = "\n".join(metadata) + "\n\n" + content

            logger.info("Successfully formatted document for LLM")
            return formatted_content

        except Exception as e:
            logger.error(f"Error formatting document {document_id} for LLM: {e}", exc_info=True)
            error_message = f"# Error Fetching Google Doc\n\nFailed to fetch or format document {document_id}: {str(e)}"
            return error_message

    def close(self) -> None:
        """Close the Google Docs API service resources."""
        if self._service:
            logger.info("Closing Google Docs API service.")
            self._service = None
            logger.info("Google Docs API service closed.")
        else:
            logger.debug("Google Docs API service was never initialized.")

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point. Ensures resources are closed."""
        self.close()
