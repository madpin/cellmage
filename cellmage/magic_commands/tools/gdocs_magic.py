"""
Google Docs magic command for CellMage.

This module provides a magic command to fetch Google Docs content directly into the notebook
and use it as context for LLM prompts.
"""

import logging
import sys
from typing import Any, Dict

# IPython imports with fallback handling
try:
    from IPython.core.magic import line_magic, magics_class
    from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

    # Define dummy decorators if IPython is not installed
    def magics_class(cls):
        return cls

    def line_magic(func):
        return func

    def magic_arguments():
        return lambda func: func

    def argument(*args, **kwargs):
        return lambda func: func


from cellmage.config import settings
from cellmage.integrations.gdocs_utils import _GDOCS_AVAILABLE, GoogleDocsUtils
from cellmage.magic_commands.tools.base_tool_magic import BaseMagics

# Create a logger
logger = logging.getLogger(__name__)


@magics_class
class GoogleDocsMagic(BaseMagics):
    """
    Magic command to fetch Google Docs content.

    This class provides the %gdocs magic command, which allows users to fetch
    Google Docs content and use it as context for LLM prompts.
    """

    def __init__(self, shell=None, **kwargs):
        """Initialize the Google Docs magic."""
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not found. GoogleDocsMagic is disabled.")
            return

        try:
            super().__init__(shell, **kwargs)
        except Exception as e:
            logger.warning(f"Error initializing GoogleDocsMagic: {e}")

        self._gdocs_utils = None
        # Check if required libraries are available
        if not _GDOCS_AVAILABLE:
            logger.warning("Required libraries for Google Docs integration not available.")
            print("══════════════════════════════════════════════════════════")
            print("❌ Required Google Docs libraries not available")
            print("══════════════════════════════════════════════════════════")
            print("• Install with: pip install cellmage[gdocs]")
            print("══════════════════════════════════════════════════════════")
        else:
            logger.info("GoogleDocsMagic initialized.")

    @property
    def gdocs_utils(self) -> GoogleDocsUtils:
        """Get the Google Docs utils instance, created on first use."""
        if self._gdocs_utils is None:
            if not _GDOCS_AVAILABLE:
                raise ImportError(
                    "The Google API packages are required but not installed. "
                    "Please install with 'pip install cellmage[gdocs]'"
                )
            self._gdocs_utils = GoogleDocsUtils()
        return self._gdocs_utils

    def _add_to_history(
        self,
        content: str,
        source_type: str,
        source_id: str,
        as_system_msg: bool = False,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Add the content to the chat history as a user or system message."""
        return super()._add_to_history(
            content=content,
            source_type=source_type,
            source_id=source_id,
            source_name="gdocs",
            id_key="gdocs_id",
            as_system_msg=as_system_msg,
        )

    @magic_arguments()
    @argument("doc_id_or_url", type=str, nargs="?", help="Google Docs document ID or URL")
    @argument(
        "--system",
        action="store_true",
        help="Add as system message instead of user message",
    )
    @argument(
        "--show",
        action="store_true",
        help="Only display the content without adding it to chat history",
    )
    @argument(
        "--search", type=str, help="Search for Google Docs files containing the specified term"
    )
    @argument(
        "--content", action="store_true", help="Retrieve and display content for search results"
    )
    @argument(
        "--max-results", type=int, default=10, help="Maximum number of search results to return"
    )
    @argument(
        "--max-content",
        type=int,
        default=3,
        help="Maximum number of documents to retrieve content for",
    )
    @argument(
        "--timeout",
        type=int,
        default=None,
        help="Request timeout in seconds (default: from config, typically 300)",
    )
    @argument("--author", type=str, help="Filter documents by author/owner email")
    @argument(
        "--created-after",
        "--created",  # Added alias for backward compatibility
        type=str,
        help="Filter documents created after this date (YYYY-MM-DD or natural language like '3 days ago')",
    )
    @argument(
        "--created-before",
        type=str,
        help="Filter documents created before this date (YYYY-MM-DD or natural language)",
    )
    @argument(
        "--modified-after",
        "--updated",  # Added alias
        "--modified",  # Added alias for backward compatibility
        type=str,
        help="Filter documents modified after this date (YYYY-MM-DD or natural language)",
    )
    @argument(
        "--modified-before",
        type=str,
        help="Filter documents modified before this date (YYYY-MM-DD or natural language)",
    )
    @argument(
        "--order-by",
        choices=["relevance", "modifiedTime", "createdTime", "name"],
        default="relevance",
        help="How to order search results",
    )
    @argument(
        "--auth-type",
        choices=["oauth", "service_account"],
        default=settings.gdocs_auth_type,
        help=f"Authentication type to use (oauth or service_account). Default: {settings.gdocs_auth_type}",
    )
    @line_magic("gdocs")
    def gdocs(self, line):
        """
        Fetch or search Google Docs content.

        Usage:
            %gdocs [doc_id_or_url]                         # Fetch a specific document by ID or URL
            %gdocs [doc_id_or_url] --system                # Add as system message
            %gdocs [doc_id_or_url] --show                  # Only display content
            %gdocs --search "term"                         # Search for documents containing "term"
            %gdocs --search "term" --max-results 20        # Search with custom result limit
            %gdocs --search "term" --content               # Search and fetch content for top documents
            %gdocs --search "term" --content --max-content 5   # Fetch content for more documents
            %gdocs --search "term" --author "email@example.com" # Filter by author
            %gdocs --search "term" --created-after "2023-01-01" # Filter by creation date
            %gdocs --search "term" --modified-before "2023-12-31" # Filter by modification date
            %gdocs --search "term" --order-by "name"       # Order results by name

        Args:
            line: Command line arguments.
        """
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython not available. Google Docs magic cannot be used.", file=sys.stderr)
            return

        if not _GDOCS_AVAILABLE:
            print(
                "❌ Required libraries for Google Docs integration not available. "
                "Install them with 'pip install cellmage[gdocs]'",
                file=sys.stderr,
            )
            return

        try:
            args = parse_argstring(self.gdocs, line)
        except Exception as e:
            print(f"❌ Error parsing arguments: {e}", file=sys.stderr)
            return

        # Check if this is a search request
        if args.search:
            try:
                # Create a fresh instance with the specified auth type and timeout
                gdocs_utils = GoogleDocsUtils(auth_type=args.auth_type, timeout=args.timeout)

                if args.timeout:
                    print(f"⏱ Using custom timeout of {args.timeout} seconds")

                print(f"🔍 Searching for documents matching: '{args.search}'")

                # We need to handle the case where --created is used instead of --created-after
                created_after_value = None
                if hasattr(args, "created") and args.created:
                    created_after_value = args.created
                elif args.created_after:
                    created_after_value = args.created_after

                # We need to handle the case where --modified is used instead of --modified-after
                modified_after_value = None
                if hasattr(args, "modified") and args.modified:
                    modified_after_value = args.modified
                elif args.modified_after:
                    modified_after_value = args.modified_after

                # Perform the search with advanced filters
                documents = gdocs_utils.search_documents(
                    search_query=args.search.replace('"', ""),  # Remove quotes from search term
                    max_results=max(args.max_results, args.max_content),
                    author=args.author,
                    created_after=created_after_value,
                    created_before=args.created_before,
                    modified_after=modified_after_value,
                    modified_before=args.modified_before,
                    order_by=args.order_by,
                )

                if not documents:
                    print(f"ℹ️ No documents found matching '{args.search}'.")
                    return

                # Display results in a formatted table
                from IPython.display import Markdown, display

                # Create a markdown table with the results
                table = [
                    "# Google Docs Search Results",
                    "",
                    "| # | Document Title | Created | Last Updated | Owner | URL |",
                    "| --- | --- | --- | --- | --- | --- |",
                ]

                # Use all documents, not just the first args.max_results
                for i, doc in enumerate(documents, 1):
                    # Try to get additional metadata if available
                    created_date = doc.get("createdTime", "N/A")
                    modified_date = doc.get("modifiedTime", "N/A")
                    owner = doc.get("owners", [{"displayName": "N/A"}])[0].get("displayName", "N/A")

                    table.append(
                        f"| {i} | {doc['name']} | {created_date} | {modified_date} | {owner} | [{doc['id']}]({doc['url']}) |"
                    )

                # Add header row after every 50 items for better readability if there are many results
                if len(documents) > 50:
                    for i in range(50, len(documents), 50):
                        if i < len(table):
                            table.insert(
                                i + 4, "| --- | --- | --- | --- | --- | --- |"
                            )  # +4 for the header rows

                # Format the search results as markdown
                search_results_md = "\n".join(table)

                # When using --show, display the results
                if args.show:
                    display(Markdown(search_results_md))
                    print(f"ℹ️ Found {len(documents)} documents matching '{args.search}'.")

                    # Don't show the "not added to history" message yet if we're going to fetch content
                    if not args.content:
                        print("ℹ️ Content displayed only. Not added to history.")
                else:
                    # Add to conversation history as a user message by default
                    # Create a unique ID for this collection of documents
                    search_id = f"gdocs_search_{args.search.replace(' ', '_')}"

                    success = self._add_to_history(
                        content=search_results_md,
                        source_type="google_docs_search_results",
                        source_id=search_id,
                        as_system_msg=args.system,
                    )

                    if success:
                        msg_type = "system" if args.system else "user"
                        print(f"✅ Found {len(documents)} documents matching '{args.search}'.")
                        print(f"✅ Google Docs search results added as {msg_type} message")
                    else:
                        print(
                            "❌ Failed to add Google Docs search results to history.",
                            file=sys.stderr,
                        )

                # Fetch content for top documents if --content is specified
                if args.content:
                    print(
                        f"📄 Fetching content for the top {min(args.max_content, len(documents))} documents... (You can change that with --max-content X)"
                    )
                    try:
                        # Use the parallel fetching method
                        docs_with_content = gdocs_utils.fetch_documents_content_parallel(
                            documents, max_docs=args.max_content
                        )

                        # Add each document content as a separate message in the conversation history
                        for doc in docs_with_content:
                            doc_title = doc["name"]
                            doc_id = doc["id"]
                            doc_url = doc["url"]
                            doc_content = doc["content"]

                            # Format the document header for clearer identification
                            header = f"# {doc_title}\nDocument ID: {doc_id}\nURL: {doc_url}\n\n"

                            # For display only (--show flag)
                            if args.show:
                                display(Markdown(header + doc_content))
                                display(Markdown("---\n" + 160 * "-" + "\n---\n"))
                                print(
                                    f"ℹ️ Content from '{doc_title}' displayed only. Not added to history."
                                )
                            else:
                                # Add to conversation history as a separate message
                                doc_message_id = f"gdocs_doc_{doc_id}"
                                success = self._add_to_history(
                                    content=header + doc_content,
                                    source_type="google_docs_document",
                                    source_id=doc_message_id,
                                    as_system_msg=args.system,
                                )

                                if success:
                                    msg_type = "system" if args.system else "user"
                                    print(f"✅ Document '{doc_title}' added as {msg_type} message")
                                else:
                                    print(
                                        f"❌ Failed to add document '{doc_title}' to history.",
                                        file=sys.stderr,
                                    )

                    except Exception as e:
                        print(f"❌ Error fetching document content: {e}", file=sys.stderr)
                        logger.exception("Error fetching document content in parallel")

                if args.show:
                    # Final confirmation after showing all content
                    print("ℹ️ All content displayed only. Not added to history.")

                return

            except ImportError as e:
                print(f"❌ Error: {str(e)}", file=sys.stderr)
            except ValueError as e:
                print(f"❌ Error: {str(e)}", file=sys.stderr)
            except RuntimeError as e:
                print(f"❌ Error: {str(e)}", file=sys.stderr)
            except Exception as e:
                print(f"❌ Unexpected error: {str(e)}", file=sys.stderr)
                logger.exception("Error in Google Docs magic search")
            return

        # Handling a specific document request
        if not args.doc_id_or_url:
            print("❌ Missing document ID or URL parameter.", file=sys.stderr)
            print('Usage: %gdocs <doc_id_or_url> or %gdocs --search "term"', file=sys.stderr)
            return

        try:
            manager = self._get_chat_manager()
            if not manager:
                print(
                    "❌ Error accessing ChatManager. Google Docs magic could not access ChatManager.",
                    file=sys.stderr,
                )
                return
        except Exception as e:
            print(f"❌ Error accessing ChatManager: {e}", file=sys.stderr)
            return

        try:
            # Create a fresh instance with the specified auth type and timeout
            gdocs_utils = GoogleDocsUtils(auth_type=args.auth_type, timeout=args.timeout)

            if args.timeout:
                print(f"⏱ Using custom timeout of {args.timeout} seconds")

            # Extract document ID if URL is provided
            try:
                doc_id = gdocs_utils.extract_document_id_from_url(args.doc_id_or_url)
            except ValueError as e:
                print(f"❌ Error: {str(e)}", file=sys.stderr)
                return

            print(f"📄 Fetching Google Doc: {doc_id}")

            # Get and format the document content
            content = gdocs_utils.format_document_for_llm(doc_id)

            if args.show:
                display(Markdown(content))
                print("ℹ️ Content displayed only. Not added to history.")
            else:
                # Add to conversation history
                success = self._add_to_history(
                    content=content,
                    source_type="google_docs",
                    source_id=doc_id,
                    as_system_msg=args.system,
                )

                if success:
                    msg_type = "system" if args.system else "user"
                    print(f"✅ Google Docs content added as {msg_type} message")
                else:
                    print("❌ Failed to add Google Docs content to history.", file=sys.stderr)

        except ImportError as e:
            print(f"❌ Error: {str(e)}", file=sys.stderr)
        except ValueError as e:
            print(f"❌ Error: {str(e)}", file=sys.stderr)
        except RuntimeError as e:
            print(f"❌ Error: {str(e)}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}", file=sys.stderr)
            logger.exception("Error in Google Docs magic")


# --- Extension Loading ---
def load_ipython_extension(ipython):
    """Register the Google Docs magics with the IPython runtime."""
    if not _IPYTHON_AVAILABLE:
        print("══════════════════════════════════════════════════════════")
        print("❌ IPython not available")
        print("══════════════════════════════════════════════════════════")
        print("• Cannot load Google Docs magics")
        print("══════════════════════════════════════════════════════════")
        return

    if not _GDOCS_AVAILABLE:
        print("══════════════════════════════════════════════════════════")
        print("❌ Google Docs API libraries not found")
        print("══════════════════════════════════════════════════════════")
        print("• Install with: pip install cellmage[gdocs]")
        print("• Google Docs magics will not be available")
        print("══════════════════════════════════════════════════════════")
        return

    try:
        gdocs_magics = GoogleDocsMagic(ipython)
        ipython.register_magics(gdocs_magics)
        print("✅ Google Docs Magics Loaded Successfully")
    except Exception as e:
        logger.exception("Failed to register Google Docs magics.")
        print(f"❌ Failed to load Google Docs Magics • Error: {e}")


def unload_ipython_extension(ipython):
    """Unregister the magics."""
    pass
