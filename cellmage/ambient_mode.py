"""
Ambient mode functionality for CellMage.

This module handles the IPython input transformers that enable "ambient mode" -
the ability to treat regular code cells as LLM prompts automatically.
"""

import logging
from typing import Any, List

# Set up logging
logger = logging.getLogger(__name__)

# Global state
_ambient_mode_enabled = False


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
    if any(
        line.strip().startswith(("%%", "%load", "%reload", "%llm_config", "%disable_llm"))
        for line in lines
    ):
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

    # Replace the cell content with code that will call process_cell_as_prompt
    # This is the magic - instead of executing the cell content directly,
    # we execute code that will send it to the LLM

    # Generate cleaner code with proper spacing and clear separation between statements
    # Use multiple approaches to find the NotebookLLMMagics instance for better reliability
    new_lines = [
        f"""import sys
try:
    # Method 1: Direct import and instance lookup
    from cellmage.integrations.ipython_magic import NotebookLLMMagics, get_chat_manager
    from IPython import get_ipython

    ip = get_ipython()
    if not ip:
        print('Error: IPython shell not available', file=sys.stderr)
        raise RuntimeError('IPython shell not available')

    # Try multiple methods to locate the magics instance
    magics_instance = None

    # Method 1: Look in registered magics (most reliable)
    for magic_type in ip.magics_manager.magics.values():
        for instance in magic_type.values():
            if isinstance(instance, NotebookLLMMagics):
                magics_instance = instance
                break
        if magics_instance:
            break

    # Method 2: Create a temporary instance as fallback
    if not magics_instance:
        try:
            # Only try this if extension is loaded but instance wasn't found
            if 'cellmage.integrations.ipython_magic' in sys.modules:
                from cellmage.integrations.ipython_magic import NotebookLLMMagics
                temp_instance = NotebookLLMMagics(ip)
                if hasattr(temp_instance, 'process_cell_as_prompt'):
                    print('Using temporary NotebookLLMMagics instance', file=sys.stderr)
                    magics_instance = temp_instance
        except Exception as temp_err:
            print(f'Failed to create temporary instance: {{temp_err}}', file=sys.stderr)

    # Process the cell content as a prompt if instance was found
    if magics_instance and hasattr(magics_instance, 'process_cell_as_prompt'):
        magics_instance.process_cell_as_prompt({repr(cell_content)})
    else:
        print('Error: Could not find registered NotebookLLMMagics instance. Please run \"%load_ext cellmage.integrations.ipython_magic\" first.', file=sys.stderr)
except RuntimeError as re:
    print(f'Runtime error: {{re}}', file=sys.stderr)
    print('You can also try restarting the kernel.', file=sys.stderr)
except ImportError as e:
    print(f'Error importing modules: {{e}}. Is cellmage installed correctly?', file=sys.stderr)
except Exception as e:
    print(f'Error during ambient mode processing: {{e}}', file=sys.stderr)"""
    ]

    return new_lines


def process_cell_as_prompt(cell_content: str, magics_instance: Any) -> None:
    """
    Process a regular code cell as an LLM prompt.
    This is a standalone version of the function that can be called
    directly by the input transformer.

    Args:
        cell_content: The content of the cell to process
        magics_instance: The NotebookLLMMagics instance to use
    """
    # Implementation in the magics class will handle this
    # This is just a placeholder for the function signature
    pass
