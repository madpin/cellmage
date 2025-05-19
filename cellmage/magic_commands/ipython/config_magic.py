"""
Configuration magic commands for CellMage.

This module provides the %llm_config line magic for configuring LLM interactions.
"""

from IPython.core.magic import line_magic, magics_class
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

from .common import IPythonMagicsBase, logger
from .config_handlers import (
    AdapterConfigHandler,
    HistoryDisplayHandler,
    ModelSetupHandler,
    OverrideConfigHandler,
    PersistenceConfigHandler,
    PersonaConfigHandler,
    SnippetConfigHandler,
    StatusDisplayHandler,
    TokenCountHandler,
)
from .config_handlers.base_dir_config_handler import BaseDirConfigHandler


@magics_class
class ConfigMagics(IPythonMagicsBase):
    """Configuration magic commands for CellMage.

    Provides the %llm_config line magic for configuring LLM settings,
    personas, snippets, model overrides, and history management.
    """

    def __init__(self, shell=None):
        super().__init__(shell)
        # Initialize handlers
        self.handlers = [
            BaseDirConfigHandler(),
            PersonaConfigHandler(),
            SnippetConfigHandler(),
            OverrideConfigHandler(),
            HistoryDisplayHandler(),
            PersistenceConfigHandler(),
            ModelSetupHandler(),
            AdapterConfigHandler(),
            StatusDisplayHandler(),
            TokenCountHandler(),
        ]

    def llm_magic(self, line, cell=None):
        """
        Placeholder for llm_magic which is expected by the registration process.

        This method delegates to the proper implementation in CoreLLMMagics.
        """
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

    @magic_arguments()
    @argument("-p", "--persona", type=str, help="Select and activate a persona by name.")
    @argument(
        "--show-persona", action="store_true", help="Show the currently active persona details."
    )
    @argument("--list-personas", action="store_true", help="List available persona names.")
    @argument("--list-mappings", action="store_true", help="List current model name mappings")
    @argument(
        "--add-mapping",
        nargs=2,
        metavar=("ALIAS", "FULL_NAME"),
        help="Add a model name mapping (e.g., --add-mapping g4 gpt-4)",
    )
    @argument(
        "--remove-mapping",
        type=str,
        help="Remove a model name mapping",
    )
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
        "--tokens",
        action="store_true",
        help="Show token count for the current conversation history.",
    )
    @argument(
        "--token",
        action="store_true",
        help="Alias for --tokens, shows token count for conversation history.",
    )
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
    @argument(
        "--auto-save",
        action="store_true",
        help="Enable automatic saving of conversations to the conversations directory.",
    )
    @argument(
        "--no-auto-save", action="store_true", help="Disable automatic saving of conversations."
    )
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
    @argument(
        "--adapter",
        type=str,
        choices=["direct", "langchain"],
        help="Switch to a different LLM adapter implementation.",
    )
    @argument("--base-dir", type=str, help="Set the base directory for all working files.")
    @line_magic("llm_config")
    def configure_llm(self, line):
        """Configure the LLM session state and manage resources."""
        try:
            args = parse_argstring(self.configure_llm, line)
            manager = self._get_manager()
        except Exception as e:
            print(f"Error parsing arguments: {e}")
            return  # Stop processing

        # Track if any action was performed
        action_taken = False

        # Process arguments through each handler
        for handler in self.handlers:
            try:
                action_taken |= handler.handle_args(args, manager)
            except Exception as e:
                logger.exception(f"Error in handler {handler.__class__.__name__}: {e}")
                print(f"❌ Error: {e}")

        # If no action was taken, show status
        if not action_taken:
            for handler in self.handlers:
                if isinstance(handler, StatusDisplayHandler):
                    handler._show_status(manager)
                    break
