"""Magic command tools for Cellmage.

This module contains tools-related magic commands such as integrations with
external services (GitHub, Jira, Confluence, etc.).
"""

import importlib
import logging
import pkgutil
from typing import List, Optional

from IPython.core.interactiveshell import InteractiveShell

logger = logging.getLogger(__name__)

# Define __all__ without importing the classes directly
# This avoids import cycles and makes the module more resilient
__all__ = [
    "BaseMagics",
    "ConfluenceMagics",
    "GDocsMagics",
    "GitHubMagics",
    "GitLabMagics",
    "ImageMagics",
    "JiraMagics",
    "SQLiteMagics",
    "WebContentMagics",
]

# We'll import these lazily when needed rather than at module initialization


def load_ipython_extension(ipython: Optional[InteractiveShell] = None) -> List[str]:
    """Load all tool magic commands for CellMage.

    This function is called when the extension is loaded with %load_ext
    and will register all the tool magic commands.

    Args:
        ipython: The IPython shell to register magics with. If None, attempts to get it.

    Returns:
        List[str]: List of loaded tool magic names (without the _magic suffix).
    """
    try:
        # Get ipython if not provided
        if ipython is None:
            from IPython import get_ipython

            ipython = get_ipython()

        if ipython is None:
            logger.warning("IPython shell not available. Cannot register tool magics.")
            return []

        # List of tool modules that should not be registered directly
        skip_modules = ["base_tools_magic", "__pycache__"]

        # Discover and load all tool magic modules
        import cellmage.magic_commands.tools as tools_pkg

        loaded_tools = []

        for finder, mod_name, _ in pkgutil.iter_modules(tools_pkg.__path__):
            if mod_name in skip_modules:
                continue

            full_name = f"{tools_pkg.__name__}.{mod_name}"
            try:
                module = importlib.import_module(full_name)

                # Check if the module defines a load_ipython_extension function
                loader = getattr(module, "load_ipython_extension", None)
                if callable(loader):
                    loader(ipython)
                    friendly_name = mod_name.replace("_magic", "")
                    loaded_tools.append(friendly_name)
                    logger.info(f"Loaded tool magic: {friendly_name}")

            except ImportError as e:
                logger.debug(f"Could not load tool magic {mod_name}: {e}")
            except Exception as e:
                logger.warning(f"Error loading tool magic {mod_name}: {e}")

        # Return loaded tools for main module to display
        return loaded_tools

    except Exception as e:
        logger.exception(f"Failed to register CellMage tool magics: {e}")
        print(f"⚠️ Error loading CellMage tool magics: {e}")
        return []
