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
    import importlib
    import pkgutil
    import sys

    try:
        # Get ipython if not provided
        if ipython is None:
            from IPython import get_ipython

            ipython = get_ipython()

        if ipython is None:
            logger.warning("IPython shell not available. Cannot register magics.")
            return

        # Initialize the ChatManager instance for this IPython session
        from .common import _init_default_manager

        # Create ChatManager and store it in the IPython user namespace
        chat_manager = _init_default_manager()
        ipython.user_ns["_cellmage_chat_manager"] = chat_manager
        logger.info("ChatManager initialized and attached to IPython user namespace")

        # First register core magic classes - we load these explicitly to ensure proper order
        from .ambient_magic import AmbientModeMagics
        from .config_magic import ConfigMagics
        from .llm_magic import CoreLLMMagics

        # Register the core magic classes
        ipython.register_magics(CoreLLMMagics(ipython))
        ipython.register_magics(ConfigMagics(ipython))
        ipython.register_magics(AmbientModeMagics(ipython))
        logger.info("Registered core magic commands")

        # List of modules we've already loaded explicitly
        core_modules = {"ambient_magic", "config_magic", "llm_magic", "__pycache__"}

        # Modules that should not be processed as magic modules (utilities, etc.)
        excluded_modules = {"common", "__pycache__"}

        # Now dynamically discover and register any additional magic modules
        import cellmage.magic_commands.ipython as magics_pkg

        for finder, mod_name, _ in pkgutil.iter_modules(magics_pkg.__path__):
            # Skip already loaded core modules and excluded utility modules
            if mod_name in core_modules or mod_name in excluded_modules:
                continue

            full_name = f"{magics_pkg.__name__}.{mod_name}"
            try:
                module = importlib.import_module(full_name)

                # Check if the module defines a load_ipython_extension function
                loader = getattr(module, "load_ipython_extension", None)
                if callable(loader):
                    loader(ipython)
                    logger.info(f"Loaded magic commands from {mod_name}")
                    continue

                # Otherwise, look for magic classes that can be registered
                for name, obj in module.__dict__.items():
                    if isinstance(obj, type) and name.endswith("Magics"):
                        try:
                            # Try to instantiate the magic class with ipython if it looks like it expects it
                            try:
                                import inspect

                                sig = inspect.signature(obj.__init__)
                                if len(sig.parameters) > 1:  # More than just self
                                    magic_instance = obj(ipython)
                                else:
                                    magic_instance = obj()
                            except Exception:
                                # Fall back to instantiating without arguments
                                magic_instance = obj()

                            ipython.register_magics(magic_instance)
                            logger.info(f"Registered {name} from {mod_name}")
                        except Exception as e:
                            logger.warning(f"Could not register {name} from {mod_name}: {e}")

            except ImportError as e:
                logger.debug(f"Skipped magic module {mod_name}: {e}")
            except Exception as e:
                logger.warning(f"Error loading magic module {mod_name}: {e}")

        logger.info("Successfully registered all CellMage IPython magics")

    except Exception as e:
        logger.exception(f"Failed to register IPython magics: {e}")
