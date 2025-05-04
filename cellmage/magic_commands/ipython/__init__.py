"""
IPython magic command modules for CellMage.

This package provides IPython magic commands for interacting with LLM systems in notebooks.
"""

import logging
from typing import Any, Optional

from IPython.core.interactiveshell import InteractiveShell

logger = logging.getLogger(__name__)


def load_magics(ipython: Optional[InteractiveShell] = None) -> None:
    """Load all IPython magic commands for CellMage.

    Args:
        ipython: The IPython shell to register magics with. If None, attempts to get it.
    """
    try:
        # Get ipython if not provided
        if ipython is None:
            from IPython import get_ipython

            ipython = get_ipython()

        if ipython is None:
            logger.warning("IPython shell not available. Cannot register magics.")
            return

        # Import and register each magic class
        from .ambient_magic import AmbientModeMagics
        from .config_magic import ConfigMagics
        from .llm_magic import CoreLLMMagics

        # Register the magic classes
        ipython.register_magics(CoreLLMMagics)
        ipython.register_magics(ConfigMagics)
        ipython.register_magics(AmbientModeMagics)

        logger.info("Successfully registered all CellMage IPython magics")

    except Exception as e:
        logger.exception(f"Failed to register IPython magics: {e}")
