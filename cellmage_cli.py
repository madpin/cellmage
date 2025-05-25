import os
import logging
import inspect
import sys # For checking sys.modules
import io # For StringIO
import contextlib # For redirect_stdout
from typing import Any, Dict, Optional, Tuple, List

from cellmage.interfaces import ContextProvider
from cellmage.config import Settings
from cellmage.resources.file_loader import FileLoader
from cellmage.storage.sqlite_store import SQLiteStore
from cellmage.adapters.direct_client import DirectLLMAdapter
from cellmage.chat_manager import ChatManager
from cellmage.models import Message # For LLM interaction

# Attempt to import LangChainAdapter, but don't fail if it's not available
try:
    from cellmage.adapters.langchain_client import LangChainAdapter
except ImportError:
    LangChainAdapter = None  # type: ignore

# IPython imports
from IPython.core.magic import Magics, magics_class, line_magic, cell_magic
from IPython.terminal.embed import InteractiveShellEmbed

# CellMage IPython extension imports
from cellmage import load_ipython_extension
from cellmage.magic_commands.ipython import load_magics
import cellmage.magic_commands.ipython.common as ipython_common_to_patch


class CliContextProvider(ContextProvider):
    """
    A context provider for command-line interface interactions.
    """

    def __init__(self) -> None:
        """
        Initializes the CLI context provider.
        """
        pass

    def get_execution_context(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Returns the execution context. For CLI, this is typically None.
        """
        return (None, None)

    def display_markdown(self, content: str) -> None:
        """
        Displays markdown content to the console.

        Args:
            content: The markdown content to display.
        """
        print(f"[Markdown]:\n{content}")

    def display_response(self, content: str) -> None:
        """
        Displays a response to the console.

        Args:
            content: The response content to display.
        """
        print(f"[Assistant]:\n{content}")

    def display_stream_start(self) -> Dict[str, Any]:
        """
        Displays a message indicating the start of a streaming response.
        """
        print("(Streaming response started...)")
        return {"streaming": True}

    def update_stream(self, display_object: Any, content: str) -> None:
        """
        Updates the stream with new content.

        Args:
            display_object: The display object (not used in CLI).
            content: The new content to display.
        """
        print(content, end='', flush=True)

    def display_status(self, status_info: Dict[str, Any]) -> None:
        """
        Displays status information to the console.

        Args:
            status_info: A dictionary containing status information.
        """
        status_parts = []
        if "status" in status_info:
            status_parts.append(f"Status: {status_info['status']}")
        if "duration_s" in status_info:
            status_parts.append(f"Duration: {status_info['duration_s']:.1f}s")
        if "model_name" in status_info:
            status_parts.append(f"Model: {status_info['model_name']}")
        if "input_tokens" in status_info and "output_tokens" in status_info:
            status_parts.append(f"Tokens: {status_info['input_tokens']}in/{status_info['output_tokens']}out")
        elif "input_tokens" in status_info:
            status_parts.append(f"Tokens: {status_info['input_tokens']}in")
        elif "output_tokens" in status_info:
            status_parts.append(f"Tokens: {status_info['output_tokens']}out")
        if "cost_usd" in status_info:
            status_parts.append(f"Cost: ${status_info['cost_usd']:.4f}")

        if status_parts:
            print("\n" + " | ".join(status_parts))
        else:
            print("\n(No status information to display)")

def _init_cli_chat_manager() -> ChatManager:
    """
    Initializes a ChatManager instance for CLI usage.
    """
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=os.environ.get("CELLMAGE_LOG_LEVEL", "INFO").upper())

    try:
        logger.info("Initializing CLI ChatManager using _init_cli_chat_manager...")
        settings = Settings()
        loader = FileLoader(settings.personas_dir, settings.snippets_dir)
        store = SQLiteStore()
        cli_context_provider = CliContextProvider()
        adapter_type = os.environ.get("CELLMAGE_ADAPTER", "direct").lower()
        llm_client: Any

        if adapter_type == "langchain" and LangChainAdapter:
            logger.info("Using LangChainAdapter.")
            llm_client = LangChainAdapter(settings=settings)
        elif adapter_type == "langchain":
            logger.warning("LangChainAdapter requested but not available/imported. Falling back to DirectLLMAdapter.")
            llm_client = DirectLLMAdapter(settings=settings)
        else:
            logger.info("Using DirectLLMAdapter.")
            llm_client = DirectLLMAdapter(settings=settings)

        manager = ChatManager(
            settings=settings,
            llm_client=llm_client,
            persona_loader=loader,
            snippet_provider=loader,
            history_store=store,
            context_provider=cli_context_provider,
        )
        # Store manager in user_ns for HelpAIMagics to access
        if get_ipython() is not None: # type: ignore
            get_ipython().user_ns['_cellmage_chat_manager'] = manager # type: ignore
        logger.info("ChatManager initialized successfully for CLI via _init_cli_chat_manager.")
        return manager
    except Exception as e:
        logger.error(f"Error initializing CLI ChatManager via _init_cli_chat_manager: {e}", exc_info=True)
        raise

EXCLUDE_NAMES_FOR_CONTEXT_VISUALIZATION = {
    'In', 'Out', 'get_ipython', 'exit', 'quit', 'shell', '__builtin__', '__builtins__',
    '_ih', '_oh', '_dh', '__name__', '__doc__', '__package__', '__loader__', '__spec__',
    '_', '__', '___', 'sys', 'os', 'inspect', 'logging', 'io', 'contextlib', # Modules imported by this script
    'CliContextProvider', '_init_cli_chat_manager', 
    'ContextVisualizerMagics', 'CliHelpMagics', 'HelpAIMagics', # This script's classes
    'ipython_common_to_patch', 'load_ipython_extension', 'load_magics', 'Magics', 
    'magics_class', 'line_magic', 'cell_magic', 'InteractiveShellEmbed', # IPython
    'Settings', 'FileLoader', 'SQLiteStore', 'DirectLLMAdapter', 'ChatManager', 'LangChainAdapter', # CellMage core
    'ContextProvider', 'Message', # CellMage models/interfaces
    '_cellmage_chat_manager', # Internal var
    'EXCLUDE_NAMES_FOR_CONTEXT_VISUALIZATION' # This constant itself
}

@magics_class
class ContextVisualizerMagics(Magics):
    @line_magic
    def show_context(self, line: str = "") -> None:
        user_ns = self.shell.user_ns
        print("Current User Namespace Context:")
        print("-------------------------------")
        found_items = False
        for name, value in user_ns.items():
            if name in EXCLUDE_NAMES_FOR_CONTEXT_VISUALIZATION or name.startswith('_'):
                if name not in {'_', '__', '___'}: continue # allow IPython history vars
            found_items = True
            try:
                type_name = type(value).__name__
                representation = ""
                if inspect.ismodule(value):
                    if name in sys.modules and name in user_ns: representation = f"<module '{value.__name__}'>"
                    elif value.__name__ not in {'builtins', 'types'}: representation = f"<module '{value.__name__}'>"
                    else: continue
                elif inspect.isfunction(value): representation = f"<function {value.__name__}>"
                elif inspect.isclass(value): representation = f"<class {value.__name__}>"
                else:
                    try: val_repr = repr(value)
                    except Exception: val_repr = "[repr error]"
                    if len(val_repr) > 60: val_repr = val_repr[:57] + "..."
                    representation = f"<{type_name}> = {val_repr}"
                if representation: print(f"  {name}: {representation}")
            except Exception as e: print(f"  {name}: [Error inspecting: {e}]")
        if not found_items: print("  (Namespace is empty or only contains excluded items)")
        print("-------------------------------")

@magics_class
class CliHelpMagics(Magics):
    @line_magic
    def cellmage_cli_help(self, line: str = "") -> None:
        help_text = """
Welcome to the CellMage CLI REPL!
-----------------------------------
This is an interactive Python environment powered by IPython, with CellMage's LLM capabilities integrated.
Basic Usage:
*   **Execute Python Code:** Type any Python code and press Enter. Example: `my_list = [1, 2, 3+4]; print(my_list)`
*   **Chat with AI (CellMage):** Use the `%%chat` magic command. Example:
    ```ipython
    %%chat
    Explain Python's Global Interpreter Lock (GIL) in simple terms.
    ```
    Use `%cellmage_help` (from the core CellMage extension) for more on CellMage magics.
*   **View Your Namespace:** `%show_context`
*   **Command History:** `%history` or `%history -n`, `%rerun <number>`, Arrow Keys.
IPython Help: `%quickref`, `object?`, `object??`, `%magic?`.
AI-Powered Help: `%%help_ai <your question about CLI or CellMage features>`
For more about CellMage's general features, refer to the main CellMage documentation.
-----------------------------------"""
        print(help_text)

@magics_class
class HelpAIMagics(Magics):
    @cell_magic
    def help_ai(self, line: str, cell: str) -> None:
        """
        Provides AI-powered help for the CellMage CLI REPL.
        Usage:
          %%help_ai [optional line question part]
          <main question in cell body>
        """
        full_question = (line + "\n" + cell).strip()
        logger = logging.getLogger(__name__)

        # 1. Gather Static Help Text
        static_help_text_content = ""
        try:
            help_magic_instance = CliHelpMagics(shell=self.shell)
            string_io = io.StringIO()
            with contextlib.redirect_stdout(string_io):
                help_magic_instance.cellmage_cli_help()
            static_help_text_content = string_io.getvalue()
        except Exception as e:
            logger.error(f"Failed to capture static help text: {e}", exc_info=True)
            static_help_text_content = "Error: Could not load static help content."

        # 2. Summarize User Namespace
        user_namespace_summary_parts: List[str] = []
        try:
            user_ns = self.shell.user_ns
            vars_summary = []
            funcs_summary = []
            classes_summary = []
            for name, value in user_ns.items():
                if name in EXCLUDE_NAMES_FOR_CONTEXT_VISUALIZATION or name.startswith('_'):
                    if name not in {'_', '__', '___'}: continue
                
                if inspect.isfunction(value): funcs_summary.append(name)
                elif inspect.isclass(value): classes_summary.append(name)
                elif not inspect.ismodule(value): # Avoid listing all imported modules
                    vars_summary.append(f"{name} ({type(value).__name__})")
            
            if vars_summary: user_namespace_summary_parts.append(f"Variables: {', '.join(vars_summary)}.")
            if funcs_summary: user_namespace_summary_parts.append(f"Functions: {', '.join(funcs_summary)}.")
            if classes_summary: user_namespace_summary_parts.append(f"Classes: {', '.join(classes_summary)}.")
        except Exception as e:
            logger.error(f"Failed to summarize user namespace: {e}", exc_info=True)
            user_namespace_summary_parts.append("Error: Could not summarize namespace.")
        
        user_namespace_summary_content = " ".join(user_namespace_summary_parts)
        if not user_namespace_summary_content:
            user_namespace_summary_content = "No user-defined variables, functions, or classes found in the current namespace."

        # 3. System Prompt
        system_prompt = f"""
        You are an AI assistant embedded in the CellMage CLI REPL.
        Your goal is to help users understand and use the REPL, its features, Python code within it, and CellMage magic commands.

        You have access to the following context:
        1. General CLI Help Information:
        {static_help_text_content}

        2. User's Current Code Context (Namespace Summary):
        {user_namespace_summary_content}

        When answering, please:
        - Be concise and clear.
        - If the question is about the user's code, refer to the "User's Current Code Context" provided.
        - If the question is about general usage, use the "General CLI Help Information."
        - If you don't know the answer or it's outside your scope as a CellMage CLI helper, say so politely.
        - Do not attempt to execute commands or modify the user's environment. You are purely for providing information.
        """

        # 4. LLM Interaction
        chat_manager: Optional[ChatManager] = self.shell.user_ns.get('_cellmage_chat_manager')

        if chat_manager and hasattr(chat_manager, 'llm_client') and chat_manager.llm_client:
            try:
                constructed_messages = [
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=full_question)
                ]
                
                # Use a model configured for Q&A, or the default if not specified
                # For now, using the chat_manager's default model
                model_to_use = chat_manager.settings.default_model
                if chat_manager.settings.default_persona_name: # use persona model if available
                    persona = chat_manager.persona_loader.get_persona(chat_manager.settings.default_persona_name)
                    if persona and persona.model:
                        model_to_use = persona.model

                display_object = chat_manager.context_provider.display_stream_start()
                full_response = ""
                for chunk in chat_manager.llm_client.chat(
                    messages=constructed_messages,
                    model=model_to_use,
                    stream=True,
                ):
                    if chunk: # Ensure chunk is not None or empty
                        chat_manager.context_provider.update_stream(display_object, chunk)
                        full_response += chunk
                # Print newline after streaming is done, and display status
                print() 
                # Note: We don't have token/cost info from this direct llm_client call easily
                # We'd need to replicate what ChatManager.chat() does for full status.
                # For now, keeping it simpler for help_ai.
                chat_manager.context_provider.display_status({"status": "completed", "model_name": model_to_use})


            except Exception as e:
                error_msg = f"Error during AI Help interaction: {e}"
                logger.error(error_msg, exc_info=True)
                if chat_manager.context_provider:
                    chat_manager.context_provider.display_response(error_msg)
                else:
                    print(error_msg) # Fallback if context_provider is somehow missing
        else:
            message = "Help AI is unavailable: ChatManager or LLM client not configured."
            logger.warning(message)
            print(message)


# Create the shell instance globally
shell = InteractiveShellEmbed(
    banner1="Welcome to the CellMage CLI REPL! Type `%cellmage_cli_help` or `%show_context` for assistance."
)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=os.environ.get("CELLMAGE_LOG_LEVEL", "INFO").upper())

    # Register custom magics first
    try:
        logger.info("Registering ContextVisualizerMagics...")
        shell.register_magics(ContextVisualizerMagics(shell=shell))
        logger.info("ContextVisualizerMagics registered.")

        logger.info("Registering CliHelpMagics...")
        shell.register_magics(CliHelpMagics(shell=shell))
        logger.info("CliHelpMagics registered.")
        
        logger.info("Registering HelpAIMagics...")
        shell.register_magics(HelpAIMagics(shell=shell))
        logger.info("HelpAIMagics registered.")

    except Exception as e:
        logger.error(f"Error registering custom magics: {e}", exc_info=True)

    # Initialize ChatManager and potentially store it in user_ns
    # This needs to happen before load_magics if HelpAIMagics needs it immediately
    # The _init_default_manager (monkeypatched to _init_cli_chat_manager)
    # is called by load_magics. _init_cli_chat_manager now stores the manager.
    
    original_init_default_manager = None
    if hasattr(ipython_common_to_patch, "_init_default_manager"):
        original_init_default_manager = ipython_common_to_patch._init_default_manager
    
    try:
        logger.info("Monkeypatching _init_default_manager for CLI context.")
        ipython_common_to_patch._init_default_manager = _init_cli_chat_manager

        logger.info("Loading CellMage magics...")
        load_magics(shell) 
        logger.info("CellMage magics loaded.")

        logger.info("Loading CellMage IPython extension...")
        load_ipython_extension(shell)
        logger.info("CellMage IPython extension loaded.")

    except Exception as e:
        logger.error(f"Error during CellMage CLI setup: {e}", exc_info=True)
        print(f"An error occurred during setup: {e}")
        print("CellMage features might not work correctly.")
    finally:
        if original_init_default_manager is not None:
            logger.info("Restoring original _init_default_manager.")
            ipython_common_to_patch._init_default_manager = original_init_default_manager
        else:
            logger.warning("Could not restore original _init_default_manager: was not found initially.")
            if hasattr(ipython_common_to_patch, "_init_default_manager") and \
               ipython_common_to_patch._init_default_manager is _init_cli_chat_manager:
                del ipython_common_to_patch._init_default_manager

    logger.info("Starting CellMage CLI REPL...")
    shell()
    logger.info("CellMage CLI REPL exited.")
