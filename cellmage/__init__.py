"""
CellMage - An intuitive LLM interface for Jupyter notebooks and IPython environments.

This package provides magic commands, conversation management, and utilities
for interacting with LLMs in Jupyter/IPython environments.
"""

import importlib
import logging
import os
from typing import Optional

from .chat_manager import ChatManager
from .config import settings  # Import settings object instead of non-existent functions

# Main managers
from .conversation_manager import ConversationManager
from .exceptions import ConfigurationError, PersistenceError, ResourceNotFoundError
from .history_manager import HistoryManager

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
    ensures that SQLite storage is used by default.
    """
    from .context_providers.ipython_context_provider import get_ipython_context_provider

    # Default to SQLite storage unless explicitly disabled
    use_file_storage = os.environ.get("CELLMAGE_USE_FILE_STORAGE", "0") == "1"

    if not use_file_storage:
        try:
            # Create SQLite-backed conversation manager
            context_provider = get_ipython_context_provider()
            manager = ConversationManager(
                context_provider=context_provider,
                storage_type="sqlite",  # Explicitly request SQLite storage
            )
            logger.info("Created default SQLite-backed conversation manager")
            return manager
        except Exception as e:
            logger.warning(f"Failed to create SQLite conversation manager: {e}")
            logger.warning("Falling back to memory-based storage")

    # Fallback to memory-based storage
    context_provider = get_ipython_context_provider()
    manager = ConversationManager(context_provider=context_provider)
    logger.info("Created memory-backed conversation manager (fallback)")
    return manager


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
