"""
Ambient mode magic commands for CellMage.

This module provides magics for enabling and disabling ambient mode, where regular code
cells are processed as LLM prompts, and the %%py magic to run cells as Python code.
"""

import sys
import time

from IPython import get_ipython
from IPython.core.magic import cell_magic, line_magic, magics_class
from IPython.core.magic_arguments import argument, magic_arguments

from cellmage.magic_commands.core import extract_metadata_for_status

from ...ambient_mode import (
    disable_ambient_mode,
    enable_ambient_mode,
    is_ambient_mode_enabled,
    register_ambient_handler,
)
from ...context_providers.ipython_context_provider import get_ipython_context_provider
from .common import _IPYTHON_AVAILABLE, IPythonMagicsBase, logger

# Global instance of AmbientModeMagics to use for the module-level function
_ambient_magic_instance = None


def get_ambient_magics_instance(shell=None):
    """
    Get or create a global instance of AmbientModeMagics.

    Args:
        shell: The IPython shell to associate with the instance

    Returns:
        An instance of AmbientModeMagics
    """
    global _ambient_magic_instance
    if _ambient_magic_instance is None:
        _ambient_magic_instance = AmbientModeMagics(shell)
    return _ambient_magic_instance


def process_cell_as_prompt(cell_content: str) -> None:
    """
    Module-level function that processes a cell as a prompt.
    This delegates to the AmbientModeMagics class instance.

    Args:
        cell_content: The content of the cell to process
    """
    instance = get_ambient_magics_instance()
    instance.process_cell_as_prompt(cell_content)


@magics_class
class AmbientModeMagics(IPythonMagicsBase):
    """Magic commands for ambient mode functionality in CellMage."""

    def __init__(self, shell=None):
        """Initialize the AmbientModeMagics class."""
        super().__init__(shell)
        # Register our module-level process_cell_as_prompt function as the ambient handler
        register_ambient_handler(process_cell_as_prompt)
        logger.info("Registered ambient handler from AmbientModeMagics")

    @magic_arguments()
    @argument("-p", "--persona", type=str, help="Select and activate a persona by name.")
    @argument(
        "--show-persona", action="store_true", help="Show the currently active persona details."
    )
    @argument("--list-personas", action="store_true", help="List available persona names.")
    @argument(
        "--set-override",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Set a temporary LLM param override (e.g., --set-override temperature 0.5).",
    )
    @argument("--remove-override", type=str, metavar="KEY", help="Remove a specific override key.")
    @argument(
        "--clear-overrides", action="store_true", help="Clear all temporary LLM param overrides."
    )
    @argument("--show-overrides", action="store_true", help="Show the currently active overrides.")
    @argument(
        "--clear-history",
        action="store_true",
        help="Clear the current chat history (keeps system prompt).",
    )
    @argument("--show-history", action="store_true", help="Display the current message history.")
    @argument(
        "--save",
        type=str,
        nargs="?",
        const=True,
        metavar="FILENAME",
        help="Save session. If no name, uses current session ID. '.md' added automatically.",
    )
    @argument(
        "--load",
        type=str,
        metavar="SESSION_ID",
        help="Load session from specified identifier (filename without .md).",
    )
    @argument("--list-sessions", action="store_true", help="List saved session identifiers.")
    @argument("--list-snippets", action="store_true", help="List available snippet names.")
    @argument(
        "--snippet",
        type=str,
        action="append",
        help="Add user snippet content before sending prompt. Can be used multiple times.",
    )
    @argument(
        "--sys-snippet",
        type=str,
        action="append",
        help="Add system snippet content before sending prompt. Can be used multiple times.",
    )
    @argument(
        "--status",
        action="store_true",
        help="Show current status (persona, overrides, history length).",
    )
    @argument("--model", type=str, help="Set the default model for the LLM client.")
    @line_magic("llm_config_persistent")
    def configure_llm_persistent(self, line):
        """
        Configure the LLM session state and activate ambient mode.

        This magic command has the same functionality as %llm_config but also
        enables 'ambient mode', which processes all regular code cells as LLM prompts.
        Use %disable_llm_config_persistent to turn off ambient mode.
        """
        # First, apply all the regular llm_config settings by importing and using ConfigMagics
        from .config_magic import ConfigMagics

        # Create a temporary ConfigMagics instance and call its configure_llm method
        config_magic = ConfigMagics(self.shell)
        config_magic.configure_llm(line)

        # Then enable ambient mode
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython not available. Cannot enable ambient mode.", file=sys.stderr)
            return

        ip = get_ipython()
        if not ip:
            print("❌ IPython shell not found. Cannot enable ambient mode.", file=sys.stderr)
            return

        if not is_ambient_mode_enabled():
            enable_ambient_mode(ip)
            # Register the handler again to ensure it's set for persistent mode
            register_ambient_handler(process_cell_as_prompt)
            print("══════════════════════════════════════════════════════════")
            print("  🔄 Ambient Mode Enabled")
            print("══════════════════════════════════════════════════════════")
            print("  • All cells will now be processed as LLM prompts")
            print("  • Cells starting with % (magic) or ! (shell) will run normally")
            print("  • Use %%py to run a specific cell as Python code")
            print("  • Use %disable_llm_config_persistent to disable ambient mode")
            print("══════════════════════════════════════════════════════════")
        else:
            print("══════════════════════════════════════════════════════════")
            print("  ℹ️  Ambient Mode Status")
            print("══════════════════════════════════════════════════════════")
            print("  • Ambient mode is already active")
            print("  • Use %disable_llm_config_persistent to disable it")
            print("══════════════════════════════════════════════════════════")

    @line_magic("disable_llm_config_persistent")
    def disable_llm_config_persistent(self, line):
        """Deactivate ambient mode (stops processing regular code cells as LLM prompts)."""
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython not available.", file=sys.stderr)
            return None

        ip = get_ipython()
        if not ip:
            print("❌ IPython shell not found.", file=sys.stderr)
            return None

        if is_ambient_mode_enabled():
            disable_ambient_mode(ip)
            print("❌ Ambient mode DISABLED. Regular cells will now be executed normally.")
        else:
            print("ℹ️ Ambient mode was not active.")

        return None

    @cell_magic("py")
    def execute_python(self, line, cell):
        """Execute the cell as normal Python code, bypassing ambient mode.

        This magic is useful when ambient mode is enabled but you want to
        execute a specific cell as regular Python code without LLM processing.

        Variables defined in this cell will be available in other cells.

        Usage:
        %%py
        # This will run as normal Python code
        x = 10
        print(f"The value is {x}")
        """
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython not available. Cannot execute cell.", file=sys.stderr)
            return

        import contextlib
        import io

        from IPython.display import Markdown

        try:
            # Get the shell from self.shell (provided by the Magics base class)
            shell = self.shell

            # Capture stdout during execution
            stdout_buffer = io.StringIO()

            # Execute with stdout capture
            with contextlib.redirect_stdout(stdout_buffer):
                logger.info("Executing cell as normal Python code via %%py magic")

                # Run the cell in the user's namespace
                result = shell.run_cell(cell)

            # Get captured stdout
            output = stdout_buffer.getvalue()

            # Handle execution errors
            if result.error_before_exec or result.error_in_exec:
                error = result.error_in_exec or result.error_before_exec
                error_msg = f"❌ Error: {error}"
                print(error_msg, file=sys.stderr)
                # Return markdown with error
                return Markdown(f"```\n{error_msg}\n```\n*Python execution failed*")

            # Format the output as markdown
            md_output = f"```\n{output.rstrip()}\n```"

            # Include the result if it's not None and different from the output
            if result.result is not None and str(result.result) != output.rstrip():
                md_output += f"\n\n*Result:* `{result.result}`"

            md_output += "\n\n*Executed Python code successfully*"

            # Return as markdown for better display in notebooks
            return Markdown(md_output)

        except Exception as e:
            error_msg = f"❌ Error executing Python cell: {e}"
            print(error_msg, file=sys.stderr)
            logger.error(f"Error during %%py execution: {e}")
            return Markdown(f"```\n{error_msg}\n```\n*Python execution failed*")

    def process_cell_as_prompt(self, cell_content: str) -> None:
        """Process a regular code cell as an LLM prompt in ambient mode."""
        if not _IPYTHON_AVAILABLE:
            return

        start_time = time.time()
        status_info = {"success": False, "duration": 0.0}
        context_provider = get_ipython_context_provider()

        try:
            manager = self._get_manager()
        except Exception as e:
            print(f"Error getting ChatManager: {e}", file=sys.stderr)
            return

        prompt = cell_content.strip()
        if not prompt:
            logger.debug("Skipping empty prompt in ambient mode.")
            return

        logger.debug(f"Processing cell as prompt in ambient mode: '{prompt[:50]}...'")

        try:
            # Call the ChatManager's chat method with default settings
            result = manager.chat(
                prompt=prompt,
                persona_name=None,  # Use default persona
                stream=True,  # Default to streaming output
                add_to_history=True,
                auto_rollback=True,
            )

            # If result is successful, mark as success
            if result:
                status_info["success"] = True
                status_info["response_content"] = result
                try:
                    from cellmage.magic_commands.core import get_last_assistant_metadata

                    history = manager.get_history()
                    last_meta = get_last_assistant_metadata(history)
                    status_info.update(extract_metadata_for_status(last_meta))
                except Exception as e:
                    logger.error(f"Error computing status bar statistics: {e}")

        except Exception as e:
            print(f"❌ LLM Error (Ambient Mode): {e}", file=sys.stderr)
            logger.error(f"Error during LLM call in ambient mode: {e}")
            status_info["response_content"] = f"Error: {str(e)}"
        finally:
            status_info["duration"] = time.time() - start_time
            # Always ensure model_used is present for the status bar
            if "model_used" not in status_info:
                status_info["model_used"] = status_info.get("model", "")
            context_provider.display_status(status_info)

    @line_magic("llm_magic")
    def llm_magic(self, line, cell=None):
        """
        Placeholder for llm_magic which is expected by the registration process.

        This method is included to satisfy the IPython magics registration system.
        The actual LLM functionality is provided by other magic methods and classes.
        """
        print(
            "ℹ️ This is a placeholder. Please use the %%llm cell magic from CoreLLMMagics instead."
        )

        # Delegate to the correct implementation if CoreLLMMagics is available
        try:
            from .llm_magic import CoreLLMMagics

            llm_magic = CoreLLMMagics(self.shell)
            if cell is not None:
                return llm_magic.execute_llm(line, cell)
            else:
                print("⚠️ The %%llm magic requires cell content. Please use it as a cell magic.")
        except Exception as e:
            logger.error(f"Error delegating to CoreLLMMagics.execute_llm: {e}")
            print(f"❌ Error: {e}")

        return None
