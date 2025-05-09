"""
Top-level magic commands package for CellMage.

This package contains all the magic commands used by CellMage.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def load_ipython_extension(ipython):
    """
    Load IPython magic commands for CellMage.

    This function is called by IPython when loading the extension
    and delegates to the appropriate modules to load all magic commands.

    Args:
        ipython: IPython shell instance
    """
    try:
        # Import and load the iPython magics
        from .ipython import load_magics

        load_magics(ipython)
        logger.info("Loaded CellMage IPython magic commands")
    except Exception as e:
        logger.exception(f"Failed to load CellMage magic commands: {e}")
        # Try to show something to the user
        print(f"⚠️ Error loading CellMage magic commands: {e}")


def unload_ipython_extension(ipython):
    """
    Unload IPython magic commands for CellMage.

    This function is called by IPython when unloading the extension.

    Args:
        ipython: IPython shell instance
    """
    try:
        # Currently no special cleanup needed for core functionality

        # But try to dynamically unload any magic modules that might need it
        import importlib
        import pkgutil

        import cellmage.magic_commands.ipython as magics_pkg

        for finder, mod_name, _ in pkgutil.iter_modules(magics_pkg.__path__):
            full_name = f"{magics_pkg.__name__}.{mod_name}"
            try:
                module = importlib.import_module(full_name)
                unloader = getattr(module, "unload_ipython_extension", None)
                if callable(unloader):
                    unloader(ipython)
                    logger.debug(f"Unloaded magic module: {mod_name}")
            except Exception:
                # Silent failure for unloading is acceptable
                pass
    except Exception as e:
        logger.debug(f"Error during magic commands unloading: {e}")
