"""
IPython magic command for fetching website content.

This module provides a magic command for fetching website content and adding it to the chat history.
"""

import logging
import sys
from datetime import datetime
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


# Import the base magic class
from cellmage.magic_commands.tools.base_tool_magic import BaseMagics

# Import WebContent utilities
try:
    from cellmage.integrations.webcontent_utils import (
        format_website_content_for_display,
        format_website_content_for_llm,
        get_website_content_fetcher,
        is_website_parsing_available,
    )

    _WEBSITE_PARSING_AVAILABLE = is_website_parsing_available()
except ImportError:
    _WEBSITE_PARSING_AVAILABLE = False

# Create a logger
logger = logging.getLogger(__name__)


@magics_class
class WebContentMagics(BaseMagics):
    """IPython magic commands for fetching website content and adding it to chat history."""

    def __init__(self, shell=None, **kwargs):
        """Initialize the website content magic utility."""
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not found. WebContentMagics are disabled.")
            return

        try:
            super().__init__(shell, **kwargs)
        except Exception as e:
            logger.warning(f"Error ?? initializing WebContentMagics: {e}")

        # Check if the required libraries are available
        if not _WEBSITE_PARSING_AVAILABLE:
            logger.warning("Required libraries for website content fetching not available.")
            print("══════════════════════════════════════════════════════════")
            print("❌ Required libraries not available")
            print("══════════════════════════════════════════════════════════")
            print("• Install with: pip install requests beautifulsoup4 markdownify trafilatura")
            print("══════════════════════════════════════════════════════════")
        else:
            logger.info("WebContentMagics initialized.")

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
            source_name="webcontent",
            id_key="webcontent_id",
            as_system_msg=as_system_msg,
        )

    @magic_arguments()
    @argument("url", type=str, nargs="?", help="URL to fetch")
    @argument(
        "--system",
        action="store_true",
        help="Add content as system message instead of user message",
    )
    @argument(
        "--show",
        action="store_true",
        help="Only show content without adding to history",
    )
    @argument(
        "--clean",
        action="store_true",
        help="Clean and extract main content from the website (default)",
    )
    @argument(
        "--raw",
        action="store_true",
        help="Get raw HTML content without cleaning",
    )
    @argument(
        "--method",
        type=str,
        default="trafilatura",
        choices=["trafilatura", "bs4", "simple"],
        help="Content extraction method (trafilatura, bs4, or simple)",
    )
    @argument(
        "--include-images",
        action="store_true",
        help="Include image references in the output",
    )
    @argument(
        "--no-links",
        action="store_true",
        help="Remove hyperlinks from the output",
    )
    @argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds",
    )
    @line_magic("webcontent")
    def webcontent_magic(self, line):
        """Fetch content from a website and add it to the chat history.

        Usage:
            %webcontent https://example.com
            %webcontent https://example.com --system
            %webcontent https://example.com --show --clean
            %webcontent https://example.com --raw
            %webcontent https://example.com --method bs4
        """
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython not available. WebContent magic cannot be used.", file=sys.stderr)
            return

        if not _WEBSITE_PARSING_AVAILABLE:
            print(
                "❌ Required libraries for website content fetching not available. "
                "Install them with 'pip install requests beautifulsoup4 markdownify trafilatura'",
                file=sys.stderr,
            )
            return

        try:
            args = parse_argstring(self.webcontent_magic, line)
        except Exception as e:
            print(f"❌ Error parsing arguments: {e}", file=sys.stderr)
            return

        if not args.url:
            print("❌ Missing URL parameter. Please provide a URL to fetch.", file=sys.stderr)
            return

        try:
            manager = self._get_chat_manager()
            if not manager:
                print(
                    "❌ Error accessing ChatManager. WebContent magic could not access ChatManager.",
                    file=sys.stderr,
                )
                return
        except Exception as e:
            print(f"❌ Error accessing ChatManager: {e}", file=sys.stderr)
            return

        content_fetcher = get_website_content_fetcher()
        if not content_fetcher:
            print(
                "❌ Required libraries for website content fetching not available. "
                "Install them with 'pip install requests beautifulsoup4 markdownify trafilatura'",
                file=sys.stderr,
            )
            return

        print(f"🌐 Fetching content from: {args.url}")

        html_content = content_fetcher.fetch_url(args.url, timeout=args.timeout)
        if not html_content:
            print(
                f"❌ Failed to fetch content from: {args.url}. Check that the URL is valid and accessible.",
                file=sys.stderr,
            )
            return

        metadata = content_fetcher.get_site_info(args.url, html_content)
        metadata["fetched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if args.raw:
            content = html_content
        else:
            print(f"🧹 Cleaning content using {args.method} method")
            content = content_fetcher.clean_content(
                html_content,
                extraction_method=args.method,
                include_images=args.include_images,
                include_links=not args.no_links,
            )

        if args.show:
            formatted_content = format_website_content_for_display(content, metadata)
            print(formatted_content)
            print("ℹ️ Content displayed only. Not added to history.")
            return

        llm_formatted_content = format_website_content_for_llm(content, metadata)
        success = self._add_to_history(
            content=llm_formatted_content,
            source_type="website",
            source_id=args.url,
            as_system_msg=args.system,
        )

        if success:
            # print(f"✅ Content from {args.url} added as {msg_type} message.")
            if metadata.get("title"):
                print(f"   Title: {metadata['title']}")
        else:
            print(f"❌ Failed to add content from {args.url} to history.", file=sys.stderr)


# --- Extension Loading ---
def load_ipython_extension(ipython):
    """Register the WebContent magics with the IPython runtime."""
    if not _IPYTHON_AVAILABLE:
        print("══════════════════════════════════════════════════════════")
        print("❌ IPython not available")
        print("══════════════════════════════════════════════════════════")
        print("• Cannot load WebContent magics")
        print("══════════════════════════════════════════════════════════")
        return

    if not _WEBSITE_PARSING_AVAILABLE:
        print("══════════════════════════════════════════════════════════")
        print("❌ Website parsing libraries not found")
        print("══════════════════════════════════════════════════════════")
        print("• Install with: pip install requests beautifulsoup4 markdownify trafilatura")
        print("• WebContent magics will not be available")
        print("══════════════════════════════════════════════════════════")
        return

    try:
        webcontent_magics = WebContentMagics(ipython)
        ipython.register_magics(webcontent_magics)
        print("✅ WebContent Magics Loaded Successfully")
    except Exception as e:
        logger.exception("Failed to register WebContent magics.")
        print(f"❌ Failed to load WebContent Magics • Error: {e}")


def unload_ipython_extension(ipython):
    """Unregister the magics."""
    pass
