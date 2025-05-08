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
    from IPython.display import Markdown, display

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


from ..config import settings
from ..utils.gdocs_utils import _GDOCS_AVAILABLE, GoogleDocsUtils
from .base_magic import BaseMagics

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
        "--auth-type",
        choices=["oauth", "service_account"],
        default=settings.gdocs_auth_type,
        help=f"Authentication type to use (oauth or service_account). Default: {settings.gdocs_auth_type}",
    )
    @line_magic("gdocs")
    def gdocs(self, line):
        """
        Fetch Google Docs content and add it to the conversation history.

        Usage:
            %gdocs [doc_id_or_url]
            %gdocs [doc_id_or_url] --system
            %gdocs [doc_id_or_url] --show

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

        if not args.doc_id_or_url:
            print("❌ Missing document ID or URL parameter.", file=sys.stderr)
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
            # Create a fresh instance with the specified auth type
            gdocs_utils = GoogleDocsUtils(auth_type=args.auth_type)

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
