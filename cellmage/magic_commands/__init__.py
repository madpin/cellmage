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
    # Currently no special cleanup needed
    pass
