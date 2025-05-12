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


def _print_extension_status(primary_loaded, core_magics, tool_magics, integrations):
    """Print a formatted summary of loaded extension components."""
    if not primary_loaded:
        print("⚠️ CellMage core functionality could not be loaded")
        return

    print("\n✅ CellMage extension v{} loaded successfully!".format(__version__))

    # Display available magic commands
    print("\n🔮 Core magic commands:")
    for cmd, desc in core_magics.items():
        print(f"  %{cmd} - {desc}")

    # Display available tool integrations
    if tool_magics:
        print("\n🧰 Available tool magic commands:")
        # Add descriptions for common tools
        tool_descriptions = {
            "jira": "Interact with Jira issues and boards",
            "confluence": "Access and update Confluence pages",
            "github": "Query GitHub repositories and issues",
            "gitlab": "Work with GitLab projects and issues",
            "gdocs": "Read from and write to Google Docs",
            "img": "Generate and manipulate images",
            "image": "Generate and manipulate images",
            "webcontent": "Extract content from web pages",
            "sqlite": "Execute SQL queries against SQLite databases",
        }

        for tool in sorted(tool_magics):
            description = tool_descriptions.get(tool, f"{tool.capitalize()} integration")
            print(f"  %{tool} - {description}")
    else:
        print("\n⚠️ No tool magic commands were loaded")

    # Display available integrations
    if integrations:
        print("\n🔌 Available integrations:")
        # Add descriptions for common integrations
        integration_descriptions = {
            "jira": "Jira API utilities",
            "confluence": "Confluence API utilities",
            "github": "GitHub API utilities",
            "gitlab": "GitLab API utilities",
            "gdocs": "Google Docs API utilities",
            "image": "Image processing utilities",
            "webcontent": "Web content utilities",
        }

        for integration in sorted(integrations):
            description = integration_descriptions.get(
                integration, f"{integration.capitalize()} utilities"
            )
            print(f"  {integration} - {description}")

    print("\nUse '%config' to configure CellMage settings")
    print("For help with specific commands, use: %command_name --help")
    print("For detailed documentation: https://cellmage.readthedocs.io/")


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

    # Print welcome message
    print("🧙 Loading CellMage extension...")

    try:
        # Load the new refactored magic commands
        primary_extension_loaded = False

        try:
            # Use the new centralized magic command loader
            from .magic_commands import load_ipython_extension as load_magics

            loaded_core, loaded_tools = load_magics(ipython)
            primary_extension_loaded = loaded_core
            if loaded_core:
                logger.info("Loaded CellMage with refactored magic commands")
                logger.info(f"Tool magics loaded: {loaded_tools}")
            else:
                logger.warning("Core magic commands not loaded properly")
                logger.warning("Falling back to SQLite implementation")
        except Exception as e:
            logger.warning(f"Failed to load refactored magic commands: {e}")
            logger.warning("Falling back to SQLite implementation")

        # Check if we should try SQLite implementation
        if not primary_extension_loaded:
            # Try to load the SQLite implementation
            try:
                from .magic_commands.tools.sqlite_magic import (
                    load_ipython_extension as load_sqlite,
                )

                load_sqlite(ipython)
                logger.info("Loaded CellMage with SQLite-based storage")
                primary_extension_loaded = True
            except Exception as e:
                logger.error(f"Failed to load SQLite extension: {e}")
                print(f"❌ Failed to load CellMage core functionality: {e}")

        # Now dynamically discover and load all available integrations
        loaded_integrations = []
        loaded_tool_magics = []

        if primary_extension_loaded:
            try:
                # Import the tools from magic_commands and get the list of loaded tools
                from .magic_commands.tools import load_ipython_extension as load_tools

                # Get the actual loaded tools rather than just the discovered ones
                try:
                    loaded_tool_magics = load_tools(ipython) or []
                    if loaded_tool_magics:
                        logger.info(f"Loaded tool magics: {loaded_tool_magics}")
                    else:
                        logger.warning("No tool magics were loaded")
                except Exception as e:
                    logger.warning(f"Error loading tool magics: {e}")

                    # Fallback to discovering tools for display
                    try:
                        import pkgutil

                        import cellmage.magic_commands.tools as tools_pkg

                        loaded_tool_magics = []

                        # Skip base tools magic and __pycache__
                        skip_tools = ["base_tools_magic", "__pycache__"]

                        # Discover tool magic files
                        for finder, mod_name, _ in pkgutil.iter_modules(tools_pkg.__path__):
                            if mod_name in skip_tools:
                                continue

                            # Extract the name without _magic for display
                            tool_name = mod_name.replace("_magic", "")
                            loaded_tool_magics.append(tool_name)

                        logger.info(f"Discovered tools (fallback): {loaded_tool_magics}")
                    except Exception as e2:
                        logger.warning(f"Error discovering tools: {e2}")
            except Exception as e:
                logger.warning(f"Error loading tool magics: {e}")

            try:
                # Import the integrations package - these provide supporting utilities
                import cellmage.integrations as integrations_pkg

                # Skip base classes and non-integrations
                skip_modules = ["__pycache__"]

                # Iterate over all modules in the integrations package
                for finder, mod_name, is_pkg in pkgutil.iter_modules(integrations_pkg.__path__):
                    if mod_name in skip_modules:
                        continue

                    # Track integration utils for display
                    if mod_name.endswith("_utils"):
                        base_name = mod_name.replace("_utils", "")
                        loaded_integrations.append(base_name)
            except Exception as e:
                logger.error(f"Error during integrations discovery: {e}")

        # Define core magic commands
        core_magics = {
            "llm/cellm": "Interact with LLMs",
            "config": "Configure CellMage settings",
            "ambient": "Toggle ambient mode",
        }

        # Print the summary using our helper function
        _print_extension_status(
            primary_extension_loaded, core_magics, loaded_tool_magics, loaded_integrations
        )

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
            import cellmage.integrations as integrations_pkg

            for finder, mod_name, is_pkg in pkgutil.iter_modules(integrations_pkg.__path__):
                full_name = f"{integrations_pkg.__name__}.{mod_name}"
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
