"""
CellMage - An intuitive LLM interface for Jupyter notebooks and IPython environments.

This package provides magic commands, conversation management, and utilities
for interacting with LLMs in Jupyter/IPython environments.
"""

import logging
import os
from typing import Optional

from .chat_manager import ChatManager
from .config import settings  # Import settings object instead of non-existent functions

# Main managers
from .conversation_manager import ConversationManager

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

    This also dynamically loads all available integrations using module discovery.
    """
    import importlib
    import pkgutil

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
            logger.warning("Falling back to SQLite implementation")

        # Check if we should try SQLite implementation
        if not primary_extension_loaded:
            # Try to load the SQLite implementation
            try:
                from .magic_commands.sqlite_magic import (
                    load_ipython_extension as load_sqlite,
                )

                load_sqlite(ipython)
                logger.info("Loaded CellMage with SQLite-based storage")
                primary_extension_loaded = True
            except Exception as e:
                logger.error(f"Failed to load SQLite extension: {e}")
                print(f"❌ Failed to load CellMage core functionality: {e}")

        # Now dynamically discover and load all available integrations
        if primary_extension_loaded:
            try:
                # Import the tools package
                import cellmage.magic_commands.tools

                # Skip sqlite_magic as it was already attempted above
                # Also skip base_tool_magic which is a base class, not an integration
                skip_modules = ["sqlite_magic", "__pycache__", "base_tool_magic"]

                # Iterate over all modules in the tools package
                for finder, mod_name, is_pkg in pkgutil.iter_modules(
                    cellmage.magic_commands.tools.__path__
                ):
                    if mod_name in skip_modules:
                        continue

                    full_name = f"{cellmage.magic_commands.tools.__name__}.{mod_name}"
                    try:
                        module = importlib.import_module(full_name)
                        loader = getattr(module, "load_ipython_extension", None)
                        if callable(loader):
                            loader(ipython)
                            logger.info(f"Loaded integration: {mod_name}")
                    except ImportError as e:
                        logger.debug(f"Skipped integration {mod_name}: {e}")
                    except Exception as e:
                        logger.warning(f"Error loading integration {mod_name}: {e}")
            except Exception as e:
                logger.error(f"Error during dynamic integration loading: {e}")

        if not primary_extension_loaded:
            print("⚠️ CellMage core functionality could not be loaded")

    except Exception as e:
        logger.error(f"Error loading CellMage extension: {e}")
        # Try to show something to the user
        print(f"⚠️ Error loading CellMage extension: {e}")


# Unload extension
def unload_ipython_extension(ipython):
    """Unregisters the magics from the IPython runtime."""
    import importlib
    import pkgutil

    try:
        # Try to unload the refactored magic commands
        try:
            from .magic_commands import unload_ipython_extension as unload_magics

            unload_magics(ipython)
            # Continue with integrations rather than returning
        except (ImportError, AttributeError):
            pass

        # Dynamically unload all integrations if possible
        try:
            import cellmage.magic_commands.tools

            for finder, mod_name, is_pkg in pkgutil.iter_modules(
                cellmage.magic_commands.tools.__path__
            ):
                full_name = f"{cellmage.magic_commands.tools.__name__}.{mod_name}"
                try:
                    module = importlib.import_module(full_name)
                    unloader = getattr(module, "unload_ipython_extension", None)
                    if callable(unloader):
                        unloader(ipython)
                        logger.info(f"Unloaded integration: {mod_name}")
                except Exception:
                    # Silent failure for unloading is acceptable
                    pass
        except Exception as e:
            logger.debug(f"Error during dynamic integration unloading: {e}")

    except Exception as e:
        logger.error(f"Error unloading CellMage extension: {e}")
