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

from ...ambient_mode import (
    disable_ambient_mode,
    enable_ambient_mode,
    is_ambient_mode_enabled,
)
from ...context_providers.ipython_context_provider import get_ipython_context_provider
from .common import _IPYTHON_AVAILABLE, IPythonMagicsBase, logger


@magics_class
class AmbientModeMagics(IPythonMagicsBase):
    """Magic commands for ambient mode functionality in CellMage."""

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

        try:
            # Get the shell from self.shell (provided by the Magics base class)
            shell = self.shell

            # Execute the cell as normal Python code in the user's namespace
            logger.info("Executing cell as normal Python code via %%py magic")

            # Run the cell in the user's namespace
            result = shell.run_cell(cell)

            # Handle execution errors
            if result.error_before_exec or result.error_in_exec:
                if result.error_in_exec:
                    print(f"❌ Error during execution: {result.error_in_exec}", file=sys.stderr)
                else:
                    print(f"❌ Error before execution: {result.error_before_exec}", file=sys.stderr)

        except Exception as e:
            print(f"❌ Error executing Python cell: {e}", file=sys.stderr)
            logger.error(f"Error during %%py execution: {e}")

        return None

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
                # Add the response content to status_info for copying
                status_info["response_content"] = result
                try:
                    history = manager.history_manager.get_history()

                    # Calculate total tokens for the entire conversation
                    total_tokens_in = 0
                    total_tokens_out = 0

                    for msg in history:
                        if msg.metadata:
                            total_tokens_in += msg.metadata.get("tokens_in", 0) or 0
                            total_tokens_out += msg.metadata.get("tokens_out", 0) or 0

                    # Set the total tokens for display in status bar
                    status_info["tokens_in"] = float(total_tokens_in)
                    status_info["tokens_out"] = float(total_tokens_out)

                    # Add API-reported cost if available (from the most recent assistant message)
                    if len(history) >= 1 and history[-1].role == "assistant":
                        status_info["cost_str"] = history[-1].metadata.get("cost_str", "")
                        status_info["model_used"] = history[-1].metadata.get("model_used", "")
                except Exception as e:
                    logger.warning(f"Error retrieving status info from history: {e}")

        except Exception as e:
            print(f"❌ LLM Error (Ambient Mode): {e}", file=sys.stderr)
            logger.error(f"Error during LLM call in ambient mode: {e}")
            # Add error message to status_info for copying
            status_info["response_content"] = f"Error: {str(e)}"
        finally:
            status_info["duration"] = time.time() - start_time
            # Display status bar
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
