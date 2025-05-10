"""
Ambient mode functionality for CellMage.

This module handles the IPython input transformers that enable "ambient mode" -
the ability to treat regular code cells as LLM prompts automatically.
"""

import logging
from importlib import import_module
from typing import Any, Callable, List

# Set up logging
logger = logging.getLogger(__name__)

# Global state
_ambient_mode_enabled = False
_ambient_handler = None


def register_ambient_handler(handler_func: Callable[[str], None]) -> None:
    """
    Register a function that will handle processing cell content in ambient mode.

    Args:
        handler_func: A function that takes a cell content string and processes it
    """
    global _ambient_handler
    _ambient_handler = handler_func
    logger.info(f"Registered ambient handler: {handler_func.__module__}.{handler_func.__name__}")


def get_ambient_handler() -> Callable[[str], None]:
    """
    Get the currently registered ambient handler function.

    Returns:
        The registered handler function or None if not registered
    """
    return _ambient_handler


def is_ambient_mode_enabled() -> bool:
    """Check if ambient mode is currently enabled."""
    global _ambient_mode_enabled
    return _ambient_mode_enabled


def enable_ambient_mode(ipython_shell: Any) -> bool:
    """
    Enable ambient mode by registering an input transformer with IPython.

    Args:
        ipython_shell: The IPython shell instance

    Returns:
        bool: True if enabled successfully, False otherwise
    """
    global _ambient_mode_enabled

    if not ipython_shell:
        logger.error("Cannot enable ambient mode: No IPython shell provided")
        return False

    # Check if an ambient handler is registered
    if _ambient_handler is None:
        logger.error("Cannot enable ambient mode: No ambient handler registered")
        return False

    # Register the transformer if it's not already registered
    transformer_func = _auto_process_cells

    # Register with input_transformers_cleanup for better compatibility
    transformer_list = ipython_shell.input_transformers_cleanup
    if transformer_func not in transformer_list:
        transformer_list.append(transformer_func)
        _ambient_mode_enabled = True
        logger.info("Ambient mode enabled")
        return True
    else:
        logger.info("Ambient mode was already enabled")
        return False


def disable_ambient_mode(ipython_shell: Any) -> bool:
    """
    Disable ambient mode by removing the input transformer from IPython.

    Args:
        ipython_shell: The IPython shell instance

    Returns:
        bool: True if disabled successfully, False otherwise
    """
    global _ambient_mode_enabled

    if not ipython_shell:
        logger.error("Cannot disable ambient mode: No IPython shell provided")
        return False

    transformer_func = _auto_process_cells
    transformer_list = ipython_shell.input_transformers_cleanup

    try:
        # Remove all instances just in case it was added multiple times
        while transformer_func in transformer_list:
            transformer_list.remove(transformer_func)

        _ambient_mode_enabled = False
        logger.info("Ambient mode disabled")
        return True
    except ValueError:
        logger.warning("Could not find ambient mode transformer to remove")
        return False
    except Exception as e:
        logger.error(f"Error disabling ambient mode: {e}")
        return False


def _auto_process_cells(lines: List[str]) -> List[str]:
    """
    IPython input transformer that processes regular code cells as LLM prompts.

    Args:
        lines: The lines of the cell being executed

    Returns:
        List[str]: The transformed lines
    """
    # Skip processing for empty cells or cells starting with % or ! (magics or shell)
    if not lines or not lines[0] or lines[0].startswith(("%", "!")):
        return lines

    # Skip processing for cells with explicit %%llm or other known magics
    # But specifically check for %%py to ensure it's processed by the py cell magic
    if any(
        line.strip().startswith(("%%llm", "%load", "%reload", "%llm_config", "%disable_llm"))
        for line in lines
    ):
        return lines

    # Special handling for the %%py magic - allow it to be processed by the py cell magic handler
    if lines and lines[0].strip().startswith("%%py"):
        logger.debug("Detected %%py magic, allowing normal execution")
        return lines

    # Skip processing for internal Jupyter functions
    cell_content = "\n".join(lines)
    if "__jupyter_exec_background__" in cell_content:
        logger.debug("Skipping ambient mode for internal Jupyter function")
        return lines

    # Skip processing for known completion/autocomplete related code patterns
    if "get_ipython().kernel.do_complete" in cell_content:
        logger.debug("Skipping ambient mode for code completion function")
        return lines

    # Replace the cell content with code that will call the ambient handler
    # This is the magic - instead of executing the cell content directly,
    # we execute code that will send it to the LLM via our handler

    # Get the module and name of the ambient handler function
    if _ambient_handler is None:
        logger.error("Ambient handler not registered, cannot process cell")
        return [
            "print('Error: Ambient handler not registered. "
            'Please run "%load_ext cellmage.integrations" first.\', file=sys.stderr)'
        ]

    handler_module = _ambient_handler.__module__
    handler_name = _ambient_handler.__name__

    new_lines = [
        f"""import sys
try:
    # Import the module containing the ambient handler
    from {handler_module} import {handler_name}
    from IPython import get_ipython

    # Verify IPython is available
    ip = get_ipython()
    if not ip:
        print('Error: IPython shell not available', file=sys.stderr)
        raise RuntimeError('IPython shell not available')

    # Call the ambient handler directly with the cell content
    {handler_name}({repr(cell_content)})
except ImportError as e:
    print(f'Error importing ambient handler: {{e}}. Is cellmage installed correctly?', file=sys.stderr)
except RuntimeError as re:
    print(f'Runtime error: {{re}}', file=sys.stderr)
    print('You can also try restarting the kernel.', file=sys.stderr)
except Exception as e:
    print(f'Error during ambient mode processing: {{e}}', file=sys.stderr)"""
    ]

    return new_lines


def process_cell_as_prompt(cell_content: str) -> None:
    """
    Process a regular code cell as an LLM prompt.
    This function just delegates to the registered ambient handler.

    Args:
        cell_content: The content of the cell to process
    """
    if _ambient_handler is not None:
        _ambient_handler(cell_content)
    else:
        logger.error("No ambient handler registered to process prompt")
        print(
            "Error: No ambient handler registered to process prompt",
            file=import_module("sys").stderr,
        )
