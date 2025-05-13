"""
Confluence integration for Cellmage.

This module provides IPython magic commands for interacting with Confluence wiki pages.
"""

import logging
import sys
from typing import List

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


# Import the base magic class
from cellmage.magic_commands.tools.base_tool_magic import BaseMagics

# Import Confluence utilities
try:
    from cellmage.integrations.confluence_utils import (
        ConfluenceClient,
        fetch_confluence_content,
        search_confluence,
    )

    _CONFLUENCE_AVAILABLE = True
except ImportError:
    _CONFLUENCE_AVAILABLE = False

# Logging setup
logger = logging.getLogger(__name__)


@magics_class
class ConfluenceMagics(BaseMagics):
    """IPython magic commands for interacting with Confluence wiki pages."""

    def __init__(self, shell):
        """Initialize the Confluence magic utility."""
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not available. Confluence magics are disabled.")
            return

        super().__init__(shell)
        try:
            self._get_manager = self._get_chat_manager
            logger.info("Confluence magics initialized successfully.")
        except Exception as e:
            self._get_manager = None
            logger.error(f"Error initializing Confluence magics: {e}")

    def _add_to_history(
        self, content: str, source_type: str, source_id: str, as_system_msg: bool = False
    ) -> bool:
        """Add the content to the chat history as a user or system message."""
        return super()._add_to_history(
            content=content,
            source_type=source_type,
            source_id=source_id,
            source_name="confluence",
            id_key="confluence_id",
            as_system_msg=as_system_msg,
        )

    def _find_messages_to_remove(
        self, history: List, source_name: str, source_type: str, source_id: str, id_key: str
    ) -> List[int]:
        """
        Find messages to remove from history based on Confluence-specific rules.

        For pages, remove any previous page with the same identifier.
        For search queries, remove all previous search results regardless of the query.
        """
        indices_to_remove = []

        if source_type == "page":
            # For pages, remove any previous page with the same identifier
            for i, msg in enumerate(history):
                if (
                    msg.metadata
                    and msg.metadata.get("source") == source_name
                    and msg.metadata.get("type") == "page"
                    and msg.metadata.get(id_key) == source_id
                ):
                    indices_to_remove.append(i)

        elif source_type == "search":
            # For search queries, remove all previous searches
            # This ensures fresh results replace old ones
            for i, msg in enumerate(history):
                if (
                    msg.metadata
                    and msg.metadata.get("source") == source_name
                    and msg.metadata.get("type") == "search"
                ):
                    indices_to_remove.append(i)

        # For other types, use standard implementation
        else:
            indices_to_remove = super()._find_messages_to_remove(
                history, source_name, source_type, source_id, id_key
            )

        return indices_to_remove

    def _handle_page_fetch(self, args, client, manager):
        """Handle fetching a specific Confluence page."""
        print("══════════════════════════════════════════════════════════")
        print(f"  📝 Fetching Confluence page: {args.identifier}")
        print("══════════════════════════════════════════════════════════")

        try:
            # Fetch the page content with markdown option if specified
            content = fetch_confluence_content(
                args.identifier, client=client, as_markdown=args.markdown
            )

            if content.startswith("Error"):
                print(f"❌ {content}", file=sys.stderr)
                return

            # Handle display-only mode
            if args.show:
                print(content)
                print("══════════════════════════════════════════════════════════")
                format_type = "Markdown" if args.markdown else "text"
                print(f"  ℹ️  Content displayed in {format_type} format (not added to history)")
                print("══════════════════════════════════════════════════════════")
                return

            # Add to history
            success = self._add_to_history(
                content=content,
                source_type="page",
                source_id=args.identifier,
                as_system_msg=args.system,
            )
            if not success:
                print("❌ Failed to add Confluence page to history.", file=sys.stderr)

        except Exception as e:
            print(f"❌ Error fetching Confluence page: {e}", file=sys.stderr)
            logger.error(f"Error in _handle_page_fetch: {e}")

    def _handle_cql_search(self, args, client, manager):
        """Handle searching Confluence with CQL."""
        print("══════════════════════════════════════════════════════════")
        print(f"  🔍 Searching Confluence with CQL: {args.cql}")
        print("══════════════════════════════════════════════════════════")

        try:
            # Run the search
            max_results = max(1, min(20, args.max))  # Limit between 1 and 20

            # Strip surrounding quotes if present to avoid double quoting
            cql_query = args.cql.strip()
            if (cql_query.startswith('"') and cql_query.endswith('"')) or (
                cql_query.startswith("'") and cql_query.endswith("'")
            ):
                cql_query = cql_query[1:-1]

            # Add info about the content inclusion mode
            content_mode = "with" if args.include_content else "without"
            format_type = "Markdown" if args.markdown else "text"
            full_content_mode = "full content" if args.fetch_full_content else "metadata only"
            print(f"  • Searching for up to {max_results} pages {content_mode} {full_content_mode}")
            print(f"  • Output format: {format_type}")

            # Fetch search results with appropriate options
            content = search_confluence(
                cql_query,
                client=client,
                max_results=max_results,
                as_markdown=args.markdown,
                include_content=args.include_content,
                fetch_full_content=args.fetch_full_content,
            )

            if content.startswith("Error") or content.startswith("No Confluence"):
                print(f"❌ {content}", file=sys.stderr)
                return

            # Handle display-only mode
            if args.show:
                print(content)
                print("══════════════════════════════════════════════════════════")
                print("  ℹ️  Search results displayed only (not added to history)")
                print("══════════════════════════════════════════════════════════")
                return

            # Add to history
            success = self._add_to_history(
                content=content,
                source_type="search",
                source_id=args.cql,
                as_system_msg=args.system,
            )
            if not success:
                print("❌ Failed to add Confluence search results to history.", file=sys.stderr)

        except Exception as e:
            print(f"❌ Error searching Confluence: {e}", file=sys.stderr)
            logger.error(f"Error in _handle_cql_search: {e}")

    @magic_arguments()
    @argument(
        "identifier",
        nargs="?",
        help="Page identifier (SPACE:Title format or page ID)",
    )
    @argument(
        "--cql",
        type=str,
        help="Confluence Query Language (CQL) search query",
    )
    @argument(
        "--max",
        type=int,
        default=5,
        help="Maximum number of results for CQL queries",
    )
    @argument(
        "--system",
        action="store_true",
        help="Add content as a system message (rather than user)",
    )
    @argument(
        "--show",
        action="store_true",
        help="Display the content without adding to history",
    )
    @argument(
        "--text",
        dest="markdown",
        action="store_false",
        default=True,
        help="Use plain text format instead of Markdown (Markdown is default)",
    )
    @argument(
        "--no-content",
        dest="include_content",
        action="store_false",
        default=True,
        help="For CQL search, return only metadata without page content",
    )
    @argument(
        "--content",
        dest="fetch_full_content",
        action="store_true",
        default=False,
        help="For CQL search, fetch full content of each page (makes additional API calls)",
    )
    @line_magic("confluence")
    def confluence_magic(self, line):
        """
        Fetch content from Confluence wiki and add it to the conversation history.

        Basic usage:
            %confluence SPACE:Page Title
            %confluence 123456789

        Options:
            --cql "space = SPACE AND title ~ 'Search Term'"  # Search using CQL
            --max 10                                         # Set max results for CQL search
            --system                                         # Add as system message
            --show                                           # Just display without adding to history
            --text                                           # Use plain text instead of Markdown (default)
            --no-content                                     # Return only metadata without page content
            --content                                        # Fetch full content of each page (additional API calls)
        """
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython not available. Confluence magic cannot be used.", file=sys.stderr)
            return

        if not _CONFLUENCE_AVAILABLE:
            print(
                "❌ Confluence utilities not available. Please check your installation.",
                file=sys.stderr,
            )
            return

        try:
            args = parse_argstring(self.confluence_magic, line)
        except Exception as e:
            print(f"❌ Error parsing arguments: {e}", file=sys.stderr)
            return

        # Try to get the manager
        try:
            manager = self._get_chat_manager()
            if not manager:
                print("❌ Confluence magic could not access ChatManager.", file=sys.stderr)
                return
        except Exception as e:
            print(f"❌ Error getting ChatManager: {e}", file=sys.stderr)
            return

        try:
            # Initialize the Confluence client
            try:
                client = ConfluenceClient()
            except ValueError as ve:
                print(f"❌ {ve}", file=sys.stderr)
                print(
                    "  Please set CONFLUENCE_URL, JIRA_USER_EMAIL, and JIRA_API_TOKEN environment variables.",
                    file=sys.stderr,
                )
                return
            except Exception as e:
                print(f"❌ Error initializing Confluence client: {e}", file=sys.stderr)
                return

            # Process the command
            if args.cql:
                self._handle_cql_search(args, client, manager)
            elif args.identifier:
                self._handle_page_fetch(args, client, manager)
            else:
                print(
                    "❌ Please provide either a page identifier or a --cql search query.",
                    file=sys.stderr,
                )
                return

        except Exception as e:
            print(f"❌ Unexpected error in Confluence magic: {e}", file=sys.stderr)
            logger.error(f"Unexpected error in Confluence magic: {e}")


# --- Extension Loading ---
def load_ipython_extension(ipython):
    """Register the Confluence magics with the IPython runtime."""
    if not _IPYTHON_AVAILABLE:
        print("IPython not available. Cannot load Confluence extension.", file=sys.stderr)
        return

    if not _CONFLUENCE_AVAILABLE:
        print(
            "Confluence utilities not available. Cannot load Confluence extension.", file=sys.stderr
        )
        return

    try:
        # Create and register the magics class
        confluence_magics = ConfluenceMagics(ipython)
        ipython.register_magics(confluence_magics)
        print("✅ Confluence Magics loaded. Use %confluence <space:page> to fetch pages.")
        logger.info("Confluence magics loaded successfully.")
    except Exception as e:
        logger.exception(f"Failed to load Confluence magics: {e}")
        print(f"❌ Failed to initialize Confluence magics: {e}", file=sys.stderr)


def unload_ipython_extension(ipython):
    """Called when the extension is unloaded."""
    # Nothing specific to do, IPython will handle unregistration
    logger.info("Unloaded Confluence magics.")
