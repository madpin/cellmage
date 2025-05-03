"""
Confluence integration for Cellmage.

This module provides IPython magic commands for interacting with Confluence wiki pages.
"""

import logging
import sys
import uuid

# IPython imports with fallback handling
try:
    from IPython.core.magic import Magics, line_magic, magics_class
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

    class DummyMagics:
        pass  # Dummy base class

    Magics = DummyMagics  # Type alias for compatibility

# Import Confluence utilities
from ..models import Message
from ..utils.confluence_utils import (
    ConfluenceClient,
    fetch_confluence_content,
    search_confluence,
)

# Logging setup
logger = logging.getLogger(__name__)


@magics_class
class ConfluenceMagics(Magics):
    """IPython magic commands for interacting with Confluence wiki pages."""

    def __init__(self, shell):
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not available. Confluence magics are disabled.")
            return

        super().__init__(shell)
        try:
            # Import here to avoid circular imports
            from ..integrations.ipython_magic import get_chat_manager

            self._get_manager = get_chat_manager
            logger.info("Confluence magics initialized successfully.")
        except Exception as e:
            self._get_manager = None
            logger.error(f"Error initializing Confluence magics: {e}")

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

        try:
            args = parse_argstring(self.confluence_magic, line)
        except Exception as e:
            print(f"❌ Error parsing arguments: {e}", file=sys.stderr)
            return

        # Try to get the manager
        try:
            if self._get_manager:
                manager = self._get_manager()
            else:
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
            msg_role = "system" if args.system else "user"
            msg = Message(
                role=msg_role,
                content=content,
                id=str(uuid.uuid4()),
                is_confluence=True,
                metadata={
                    "source": f"confluence:{args.identifier}",
                    "format": "markdown" if args.markdown else "text",
                },
            )
            manager.history_manager.add_message(msg)

            # Print success message with preview
            format_type = "Markdown" if args.markdown else "text"
            print(
                f"✅ Confluence content added to conversation as {msg_role} message ({format_type} format)"
            )
            preview = content.replace("\n", " ")[:100]
            if len(content) > 100:
                preview += "..."
            print(f"  📄 Content: {preview}")
            print("══════════════════════════════════════════════════════════")

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
            msg_role = "system" if args.system else "user"
            msg = Message(
                role=msg_role,
                content=content,
                id=str(uuid.uuid4()),
                is_confluence=True,
                metadata={
                    "source": f"confluence_search:{args.cql}",
                    "format": "markdown" if args.markdown else "text",
                    "include_content": args.include_content,
                    "fetch_full_content": args.fetch_full_content,
                },
            )
            manager.history_manager.add_message(msg)

            # Print success message with result count
            if "Result 1:" in content:
                result_count = content.count("Result ")
                print(f"✅ {result_count} Confluence search results added as {msg_role} message")
            else:
                print(f"✅ Confluence search results added as {msg_role} message")

            # Display format information
            print(f"  • Format: {format_type}")
            print(
                f"  • Content inclusion: {'Yes' if args.include_content else 'No (metadata only)'}"
            )
            print(f"  • Full content: {'Yes' if args.fetch_full_content else 'No'}")
            print("══════════════════════════════════════════════════════════")

        except Exception as e:
            print(f"❌ Error searching Confluence: {e}", file=sys.stderr)
            logger.error(f"Error in _handle_cql_search: {e}")

    def _convert_to_markdown(self, content):
        """Convert content to Markdown format."""
        # Placeholder for Markdown conversion logic
        return content


# Extension loading functions
def load_ipython_extension(ipython):
    """Register the magics with the IPython kernel."""
    if not _IPYTHON_AVAILABLE:
        print("IPython not available. Cannot load Confluence extension.", file=sys.stderr)
        return

    try:
        # Create and register the magics class
        confluence_magics = ConfluenceMagics(ipython)
        ipython.register_magics(confluence_magics)
        logger.info("Confluence magics loaded successfully.")
    except Exception as e:
        logger.exception(f"Failed to load Confluence magics: {e}")
        print(f"❌ Failed to initialize Confluence magics: {e}", file=sys.stderr)


def unload_ipython_extension(ipython):
    """Called when the extension is unloaded."""
    # Nothing specific to do, IPython will handle unregistration
    logger.info("Unloaded Confluence magics.")
