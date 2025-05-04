"""
CellMage - An intuitive LLM interface for Jupyter notebooks and IPython environments.

This package provides magic commands, conversation management, and utilities
for interacting with LLMs in Jupyter/IPython environments.
"""

import importlib
import logging
import os
from typing import Optional

# Remove direct import of ChatManager
from .config import settings  # Import settings object instead of non-existent functions

# Main managers
from .conversation_manager import ConversationManager
from .exceptions import ConfigurationError, PersistenceError, ResourceNotFoundError
# Removed import of HistoryManager which has been deprecated

# Core components
from .models import Message

# Storage managers
from .storage import markdown_store, memory_store, sqlite_store

# Setup logging early
from .utils.logging import setup_logging

# Version import
from .version import __version__

setup_logging()

# Initialize logger
logger = logging.getLogger(__name__)


# Default SQLite-backed storage
def get_default_conversation_manager() -> ConversationManager:
    """
    Returns a default conversation manager, using SQLite storage.

    This is the preferred way to get a conversation manager as it
    ensures that SQLite storage is used by default and includes
    all necessary components for LLM interaction.
    
    Returns:
        A fully configured ConversationManager instance
    """
    from .context_providers.ipython_context_provider import get_ipython_context_provider

    # Initialize components
    context_provider = get_ipython_context_provider()
    
    # Determine which adapter to use
    adapter_type = os.environ.get("CELLMAGE_ADAPTER", "direct").lower()
    logger.info(f"Initializing default ConversationManager with adapter type: {adapter_type}")

    # Create default dependencies
    try:
        from .resources.file_loader import FileLoader
        loader = FileLoader(settings.personas_dir, settings.snippets_dir)
        
        # Initialize the appropriate LLM client adapter
        from .interfaces import LLMClientInterface
        llm_client = None

        if adapter_type == "langchain":
            try:
                from .adapters.langchain_client import LangChainAdapter
                llm_client = LangChainAdapter(default_model=settings.default_model)
                logger.info("Using LangChain adapter")
            except ImportError:
                # Fall back to Direct adapter if LangChain is not available
                logger.warning(
                    "LangChain adapter requested but not available. Falling back to Direct adapter."
                )
                from .adapters.direct_client import DirectLLMAdapter
                llm_client = DirectLLMAdapter(default_model=settings.default_model)
        else:
            # Default case: use Direct adapter
            from .adapters.direct_client import DirectLLMAdapter
            llm_client = DirectLLMAdapter(default_model=settings.default_model)
            logger.info("Using Direct adapter")
        
        # Default to SQLite storage unless explicitly disabled
        use_file_storage = os.environ.get("CELLMAGE_USE_FILE_STORAGE", "0") == "1"

        if not use_file_storage:
            try:
                # Create SQLite-backed conversation manager with all components
                manager = ConversationManager(
                    context_provider=context_provider,
                    storage_type="sqlite",  # Explicitly request SQLite storage
                    settings=settings,
                    llm_client=llm_client,
                    persona_loader=loader,
                    snippet_provider=loader,
                )
                logger.info("Created default SQLite-backed conversation manager with LLM capabilities")
                return manager
            except Exception as e:
                logger.warning(f"Failed to create SQLite conversation manager: {e}")
                logger.warning("Falling back to memory-based storage")

        # Fallback to memory-based storage, but still with LLM capabilities
        manager = ConversationManager(
            context_provider=context_provider,
            storage_type="memory",
            settings=settings,
            llm_client=llm_client,
            persona_loader=loader,
            snippet_provider=loader,
        )
        logger.info("Created memory-backed conversation manager with LLM capabilities (fallback)")
        return manager
    except Exception as e:
        # Last resort: create minimal conversation manager
        logger.error(f"Failed to initialize full ConversationManager: {e}")
        logger.warning("Creating minimal conversation manager without LLM capabilities")
        return ConversationManager(context_provider=context_provider)


def get_default_manager() -> ConversationManager:
    """
    Returns a default manager instance (backward compatibility function).
    
    This function now returns a ConversationManager instance but maintains
    the same function name for backward compatibility with code that
    previously used ChatManager.
    
    Returns:
        A fully configured ConversationManager instance
    """
    import warnings
    warnings.warn(
        "get_default_manager() is deprecated and will be removed in a future version. "
        "Use get_default_conversation_manager() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return get_default_conversation_manager()


# This function ensures backwards compatibility
def load_ipython_extension(ipython):
    """
    Registers the magics with the IPython runtime.

    By default, this now loads the SQLite-backed implementation for improved
    conversation management. For legacy file-based storage, set the
    CELLMAGE_USE_FILE_STORAGE=1 environment variable.

    This also loads all available integrations (Jira, GitLab, GitHub, etc.)
    """
    try:
        # Load the new refactored magic commands
        primary_extension_loaded = False

        try:
            # Use the new centralized magic command loader
            from .magic_commands import load_ipython_extension as load_magics

            load_magics(ipython)
            logger.info("Loaded CellMage with refactored magic commands")
            primary_extension_loaded = True
        except Exception as e:
            logger.warning(f"Failed to load refactored magic commands: {e}")
            logger.warning("Falling back to legacy implementation")

        # Check if we should prefer the SQLite implementation (legacy fallback path)
        if not primary_extension_loaded:
            use_sqlite = os.environ.get("CELLMAGE_USE_SQLITE", "1") == "1"

            if use_sqlite:
                # Try to load the SQLite implementation first
                try:
                    from .integrations.sqlite_magic import (
                        load_ipython_extension as load_sqlite,
                    )

                    load_sqlite(ipython)
                    logger.info("Loaded CellMage with SQLite-based storage (legacy)")
                    primary_extension_loaded = True
                except Exception as e:
                    logger.warning(f"Failed to load SQLite extension: {e}")
                    logger.warning("Falling back to legacy implementation")

            # Load legacy implementation if SQLite failed or not requested
            if not primary_extension_loaded:
                try:
                    from .integrations.ipython_magic import (
                        load_ipython_extension as load_legacy,
                    )

                    load_legacy(ipython)
                    logger.info("Loaded CellMage with legacy storage")
                    primary_extension_loaded = True
                except Exception as e:
                    logger.error(f"Failed to load legacy implementation: {e}")
                    print(f"❌ Failed to load CellMage core functionality: {e}")

        # Now load additional integrations if available

        # 1. Try to load Jira integration
        try:
            from .integrations.jira_magic import load_ipython_extension as load_jira

            load_jira(ipython)
            logger.info("Loaded Jira integration")
        except ImportError:
            logger.info("Jira package not available. Jira integration not loaded.")
        except Exception as e:
            logger.warning(f"Failed to load Jira integration: {e}")

        # 2. Try to load GitLab integration
        try:
            from .integrations.gitlab_magic import load_ipython_extension as load_gitlab

            load_gitlab(ipython)
            logger.info("Loaded GitLab integration")
        except ImportError:
            logger.info("GitLab package not available. GitLab integration not loaded.")
        except Exception as e:
            logger.warning(f"Failed to load GitLab integration: {e}")

        # 3. Try to load GitHub integration
        try:
            from .integrations.github_magic import load_ipython_extension as load_github

            load_github(ipython)
            logger.info("Loaded GitHub integration")
        except ImportError:
            logger.info("GitHub package not available. GitHub integration not loaded.")
        except Exception as e:
            logger.warning(f"Failed to load GitHub integration: {e}")

        # 4. Try to load Confluence integration
        try:
            from .integrations.confluence_magic import (
                load_ipython_extension as load_confluence,
            )

            load_confluence(ipython)
            logger.info("Loaded Confluence integration")
        except ImportError:
            logger.info("Confluence package not available. Confluence integration not loaded.")
        except Exception as e:
            logger.warning(f"Failed to load Confluence integration: {e}")

        if not primary_extension_loaded:
            print("⚠️ CellMage core functionality could not be loaded")

    except Exception as e:
        logger.error(f"Error loading CellMage extension: {e}")
        # Try to show something to the user
        print(f"⚠️ Error loading CellMage extension: {e}")


# Unload extension
def unload_ipython_extension(ipython):
    """Unregisters the magics from the IPython runtime."""
    try:
        # Try to unload the refactored magic commands
        try:
            from .magic_commands import unload_ipython_extension as unload_magics

            unload_magics(ipython)
            return
        except (ImportError, AttributeError):
            pass

        # Try to unload SQLite extension as fallback
        try:
            from .integrations.sqlite_magic import (
                unload_ipython_extension as unload_sqlite,
            )

            unload_sqlite(ipython)
            return
        except (ImportError, AttributeError):
            pass

        # Fall back to legacy unload
        from .integrations.ipython_magic import (
            unload_ipython_extension as unload_legacy,
        )

        unload_legacy(ipython)
    except Exception as e:
        logger.error(f"Error unloading CellMage extension: {e}")
