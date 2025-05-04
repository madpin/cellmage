"""
Common utilities and functions for IPython magic commands in CellMage.

This module contains shared functionality used across the various magic command modules.
"""

import logging
import os
import sys
from typing import Any, Dict, Optional

# IPython imports with fallback handling
try:
    from IPython.core.magic import Magics

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

    class DummyMagics:
        pass  # Dummy base class

    Magics = DummyMagics  # Type alias for compatibility

from ...chat_manager import ChatManager
from ...context_providers.ipython_context_provider import get_ipython_context_provider

# Project imports
from ...integrations.base_magic import BaseMagics

# Logging setup
logger = logging.getLogger(__name__)

# --- Global Instance Management ---
_chat_manager_instance: Optional[ChatManager] = None
_initialization_error: Optional[Exception] = None


def _init_default_manager() -> ChatManager:
    """Initializes the default ChatManager instance using default components."""
    global _initialization_error
    try:
        # Import necessary components dynamically only if needed
        from ...config import settings
        from ...resources.file_loader import FileLoader
        from ...storage.sqlite_store import SQLiteStore

        # Determine which adapter to use
        adapter_type = os.environ.get("CELLMAGE_ADAPTER", "direct").lower()

        logger.info(f"Initializing default ChatManager with adapter type: {adapter_type}")

        # Create default dependencies
        loader = FileLoader(settings.personas_dir, settings.snippets_dir)

        # Use SQLiteStore as default storage
        store = SQLiteStore()  # Use default path from settings
        logger.info("Using SQLite as default storage backend")

        context_provider = get_ipython_context_provider()

        # Initialize the appropriate LLM client adapter
        from ...interfaces import LLMClientInterface

        llm_client: Optional[LLMClientInterface] = None

        if adapter_type == "langchain":
            try:
                from ...adapters.langchain_client import LangChainAdapter

                llm_client = LangChainAdapter(default_model=settings.default_model)
                logger.info("Using LangChain adapter")
            except ImportError:
                # Fall back to Direct adapter if LangChain is not available
                logger.warning(
                    "LangChain adapter requested but not available. Falling back to Direct adapter."
                )
                from ...adapters.direct_client import DirectLLMAdapter

                llm_client = DirectLLMAdapter(default_model=settings.default_model)
        else:
            # Default case: use Direct adapter
            from ...adapters.direct_client import DirectLLMAdapter

            llm_client = DirectLLMAdapter(default_model=settings.default_model)
            logger.info("Using Direct adapter")

        manager = ChatManager(
            settings=settings,
            llm_client=llm_client,
            persona_loader=loader,
            snippet_provider=loader,
            history_store=store,
            context_provider=context_provider,
        )
        logger.info("Default ChatManager initialized successfully with SQLite storage.")
        _initialization_error = None  # Clear previous error on success
        return manager
    except Exception as e:
        logger.exception("FATAL: Failed to initialize default NotebookLLM ChatManager.")
        _initialization_error = e  # Store the error
        raise RuntimeError(
            f"NotebookLLM setup failed. Please check configuration and logs. Error: {e}"
        ) from e


def get_chat_manager() -> ChatManager:
    """Gets or creates the singleton ChatManager instance."""
    global _chat_manager_instance
    if _chat_manager_instance is None:
        if _initialization_error:
            raise RuntimeError(
                f"NotebookLLM previously failed to initialize: {_initialization_error}"
            ) from _initialization_error
        logger.debug("ChatManager instance not found, attempting initialization.")
        _chat_manager_instance = _init_default_manager()

    return _chat_manager_instance


class IPythonMagicsBase(BaseMagics):
    """Base class for all IPython magic commands in CellMage."""

    def __init__(self, shell):
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not found. NotebookLLM magics are disabled.")
            return

        super().__init__(shell)
        try:
            get_chat_manager()
            logger.info(
                f"{self.__class__.__name__} initialized and ChatManager accessed successfully."
            )
        except Exception as e:
            logger.error(f"Error initializing NotebookLLM during magic setup: {e}")

    def _get_manager(self) -> ChatManager:
        """Helper to get the manager instance, with clear error handling."""
        if not _IPYTHON_AVAILABLE:
            raise RuntimeError("IPython not available")

        try:
            return get_chat_manager()
        except Exception as e:
            print("❌ NotebookLLM Error: Could not get Chat Manager.", file=sys.stderr)
            print(f"   Reason: {e}", file=sys.stderr)
            print(
                "   Please check your configuration (.env file, API keys, directories) and restart the kernel.",
                file=sys.stderr,
            )
            raise RuntimeError("NotebookLLM manager unavailable.") from e

    def _prepare_runtime_params(self, args) -> Dict[str, Any]:
        """Extract runtime parameters from args and convert to dictionary.

        This builds a dictionary of parameters that can be passed to the LLM client.
        """
        runtime_params = {}

        # Handle simple parameters
        if hasattr(args, "temperature") and args.temperature is not None:
            runtime_params["temperature"] = args.temperature

        if hasattr(args, "max_tokens") and args.max_tokens is not None:
            runtime_params["max_tokens"] = args.max_tokens

        # Handle arbitrary parameters from --param
        if hasattr(args, "param") and args.param:
            for key, value in args.param:
                # Try to convert string values to appropriate types
                try:
                    # First try to convert to int or float if it looks numeric
                    if "." in value:
                        parsed_value = float(value)
                    else:
                        try:
                            parsed_value = int(value)
                        except ValueError:
                            parsed_value = value
                except ValueError:
                    parsed_value = value

                runtime_params[key] = parsed_value

        return runtime_params
