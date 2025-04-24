# --- Imports ---
import sys
import uuid
import time
import logging
import shlex # For safer parsing of magic line args
from typing import Optional, Tuple, Dict, Any, List

try:
    from IPython import get_ipython
    from IPython.core.magic import Magics, line_magic, cell_magic, magics_class
    from IPython.core.magic_arguments import (
        argument, magic_arguments, parse_argstring, argument_group
    )
    from IPython.display import display, Markdown, HTML, update_display
    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False
    # Define dummy decorators if IPython is not installed, so the file can still be imported
    # This allows checking functionality even without IPython (e.g., basic linting)
    def magics_class(cls): return cls
    def line_magic(func): return func
    def cell_magic(func): return func
    def magic_arguments(): return lambda func: func
    def argument(*args, **kwargs): return lambda func: func
    class Magics: pass # Dummy base class

# --- Project Imports ---
# Use absolute imports relative to the package root
from ..chat_manager import ChatManager
from ..interfaces import ContextProvider, StreamCallbackHandler
from ..exceptions import NotebookLLMError, ResourceNotFoundError, ConfigurationError, LLMInteractionError, PersistenceError
from ..models import Message # For type hints if needed

# --- Logging ---
logger = logging.getLogger(__name__)

# --- Global Instance Management ---
# Global instance (or factory-created) - needs careful management in IPython
# A function to get/create the manager instance is generally safer.
_chat_manager_instance: Optional[ChatManager] = None
_initialization_error: Optional[Exception] = None

def _init_default_manager() -> ChatManager:
    """Initializes the default ChatManager instance using default components."""
    global _initialization_error
    try:
        # Import necessary components dynamically only if needed
        from ..config import settings
        from ..adapters.direct_client import DirectLLMAdapter
        from ..resources.file_loader import FileLoader # Default file-based loaders
        from ..storage.markdown_store import MarkdownStore # Default markdown store

        logger.info("Initializing default ChatManager components...")

        # Create default dependencies
        # Error handling for directory access/creation happens in components now
        loader = FileLoader(settings.personas_dir, settings.snippets_dir)
        store = MarkdownStore(settings.save_dir)
        client = DirectLLMAdapter() # Relies on settings/env vars
        context_provider = IPythonContextProvider() # Provide IPython context

        manager = ChatManager(
            settings=settings,
            llm_client=client,
            persona_loader=loader,
            snippet_provider=loader,
            history_store=store,
            context_provider=context_provider
            # Initial persona/session ID could be loaded from config/env later
        )
        logger.info("Default ChatManager initialized successfully.")
        _initialization_error = None # Clear previous error on success
        return manager
    except Exception as e:
         logger.exception("FATAL: Failed to initialize default NotebookLLM ChatManager.")
         _initialization_error = e # Store the error
         # Re-raise a more user-friendly error for the magic command context
         raise RuntimeError(f"NotebookLLM setup failed. Please check configuration and logs. Error: {e}") from e

def get_chat_manager() -> ChatManager:
    """Gets or creates the singleton ChatManager instance."""
    global _chat_manager_instance
    if _chat_manager_instance is None:
        if _initialization_error:
            # If initialization failed before, raise the stored error
            raise RuntimeError(f"NotebookLLM previously failed to initialize: {_initialization_error}") from _initialization_error
        logger.debug("ChatManager instance not found, attempting initialization.")
        _chat_manager_instance = _init_default_manager() # This might raise RuntimeError

    return _chat_manager_instance

# --- IPython Specific Implementations ---

class IPythonContextProvider(ContextProvider):
    """
    Provides execution context from IPython/Jupyter environments.
    
    Handles cell IDs, execution counts, and displaying responses.
    """
    
    # Potential metadata keys where cell IDs might be found
    _POTENTIAL_CELL_ID_KEYS = [
        "cellId",
        "vscode_cell_id",
        "google_colab_cell_id",
        "metadata"
    ]
    
    def __init__(self):
        """Initialize the IPython context provider."""
        self.logger = logging.getLogger(__name__)
        
        if not _IPYTHON_AVAILABLE:
            self.logger.warning("IPython not available, some features will be limited.")
            
    def get_execution_context(self) -> Tuple[Optional[int], Optional[str]]:
        """
        Get the current execution context.
        
        Returns:
            Tuple of (execution_count, cell_id)
        """
        exec_count: Optional[int] = None
        cell_id: Optional[str] = None
        
        if not _IPYTHON_AVAILABLE:
            self.logger.debug("IPython not available, cannot get execution context.")
            return exec_count, cell_id
            
        try:
            ipython = get_ipython()
            if not ipython:
                self.logger.debug("Not running in an IPython environment.")
                return exec_count, cell_id  # Not in IPython
                
            # Get Execution Count
            if hasattr(ipython, "execution_count"):
                exec_count = ipython.execution_count
                
            # Get Cell ID by examining various metadata locations
            if (
                hasattr(ipython, "kernel")
                and hasattr(ipython.kernel, "shell")
                and hasattr(ipython.kernel.shell, "parent_header")
                and isinstance(ipython.kernel.shell.parent_header, dict)
            ):
                # Initial metadata sources to search
                metadata = ipython.kernel.shell.parent_header.get("metadata", {})
                search_pools = [ipython.kernel.shell.parent_header, metadata]
                
                # Add nested metadata sources
                if isinstance(metadata.get("metadata"), dict):
                    search_pools.append(metadata["metadata"])
                if isinstance(metadata.get("colab"), dict):
                    search_pools.append(metadata["colab"])
                    
                # Search for cell ID in all possible locations
                found_id = False
                for pool in search_pools:
                    if not isinstance(pool, dict):
                        continue
                    
                    # Check known cell ID keys
                    for key in self._POTENTIAL_CELL_ID_KEYS:
                        potential_id = pool.get(key)
                        if isinstance(potential_id, str) and potential_id:
                            cell_id = potential_id
                            found_id = True
                            break
                    
                    # Look for VS Code specific cell ID format
                    if not found_id:
                        for value in pool.values():
                            if isinstance(value, str) and value.startswith("vscode-notebook-cell:"):
                                cell_id = value
                                found_id = True
                                break
                                
                    if found_id:
                        break
                        
                if cell_id:
                    self.logger.debug(f"Detected Cell ID: {cell_id}")
                else:
                    self.logger.debug("Could not detect cell ID")
        except Exception as e:
            self.logger.warning(f"Error fetching execution context: {e}")
            
        return exec_count, cell_id
        
    def display_markdown(self, content: str) -> None:
        """
        Display markdown content.
        
        Args:
            content: Markdown content to display
        """
        if _IPYTHON_AVAILABLE:
            try:
                display(Markdown(content))
            except Exception as e:
                self.logger.error(f"Error displaying markdown: {e}")
                print(content)  # Fallback to print
        else:
            print(content)
            
    def display_response(self, content: str) -> None:
        """
        Display an assistant response.
        
        Args:
            content: Response content to display
        """
        if _IPYTHON_AVAILABLE:
            try:
                display(Markdown(f"**Assistant:**\n{content}"))
            except Exception as e:
                self.logger.error(f"Error displaying response: {e}")
                print(f"Assistant:\n{content}")  # Fallback to print
        else:
            print(f"Assistant:\n{content}")
            
    def display_stream_start(self) -> Any:
        """
        Set up display for a streaming response.
        
        Returns:
            Display object for updating the stream
        """
        if _IPYTHON_AVAILABLE:
            try:
                return display(Markdown("**Assistant (Streaming):**\n"), display_id=True)
            except Exception as e:
                self.logger.error(f"Error setting up stream display: {e}")
                print("Assistant (Streaming): ", end="", flush=True)
                return None
        else:
            print("Assistant (Streaming): ", end="", flush=True)
            return None
            
    def update_stream(self, display_object: Any, content: str) -> None:
        """
        Update a streaming display with new content.
        
        Args:
            display_object: The display object from display_stream_start
            content: The content to display
        """
        if _IPYTHON_AVAILABLE and display_object:
            try:
                display_object.update(Markdown(f"**Assistant:**\n{content}"))
            except Exception as e:
                self.logger.error(f"Error updating stream display: {e}")
                print(content, end="", flush=True)
        else:
            print(content, end="", flush=True)
            
    def display_status(self, success: bool, duration: float, tokens_in: int, tokens_out: int, cost_mili_cents: int) -> None:
        """
        Display a status bar with information about the LLM call.
        
        Args:
            success: Whether the call succeeded
            duration: Time taken in seconds
            tokens_in: Number of input tokens
            tokens_out: Number of output tokens
            cost_mili_cents: Cost in millicents
        """
        # Determine display cost unit based on the value
        if cost_mili_cents < 100000:
            cost_str = f"{cost_mili_cents / 1000:.2f} cents"
        else:
            cost_str = f"{cost_mili_cents / 100000:.2f} USD"
            
        # Set status appearance based on success
        if success:
            status_text = (
                f"✅ Success! Ran in {duration:.2f}s. "
                f"Tokens In: {tokens_in}, Tokens Out: {tokens_out}, Cost: {cost_str}"
            )
            bg_color = "#2e7d32"  # Dark green
            border_color = "#1b5e20"  # Darker green
            text_color = "#ffffff"  # White
        else:
            status_text = (
                f"⚠️ Warning! Ran in {duration:.2f}s. "
                f"Tokens In: {tokens_in}, Tokens Out: {tokens_out}, Cost: {cost_str}"
            )
            bg_color = "#c62828"  # Dark red
            border_color = "#8e0000"  # Darker red
            text_color = "#ffffff"  # White
            
        # Create HTML for status bar
        status_html = f"""
        <div style="
            background-color: {bg_color};
            border: 1px solid {border_color};
            color: {text_color};
            padding: 8px;
            margin-top: 10px;
            border-radius: 4px;
            font-family: sans-serif;
        ">
            {status_text}
        </div>
        """
        
        if _IPYTHON_AVAILABLE:
            try:
                display(HTML(status_html))
            except Exception as e:
                self.logger.error(f"Error displaying status: {e}")
                print(status_text)  # Fallback to print
        else:
            print(status_text)

# --- Magic Class ---

if _IPYTHON_AVAILABLE: # Only define the class if IPython is installed
    @magics_class
    class NotebookLLMMagics(Magics):
        """IPython Magics for interacting with the NotebookLLM ChatManager."""

        def __init__(self, shell):
            super().__init__(shell)
            # Attempt to initialize the manager early so setup errors are noticed sooner.
            # However, actual usage should call _get_manager() to handle errors gracefully.
            try:
                 get_chat_manager()
                 logger.info("NotebookLLMMagics initialized and ChatManager accessed successfully.")
            except Exception as e:
                 logger.error(f"Error initializing NotebookLLM during magic setup: {e}")
                 # Don't prevent magics from loading, but commands will likely fail.
                 # The error is stored in _initialization_error.

        def _get_manager(self) -> ChatManager:
            """Helper to get the manager instance, raising clearly if initialization failed."""
            try:
                # This will raise RuntimeError if _initialization_error is set
                return get_chat_manager()
            except Exception as e:
                # Provide a user-friendly error message in the notebook
                print(f"❌ NotebookLLM Error: Could not get Chat Manager.", file=sys.stderr)
                print(f"   Reason: {e}", file=sys.stderr)
                print(f"   Please check your configuration (.env file, API keys, directories) and restart the kernel.", file=sys.stderr)
                raise RuntimeError("NotebookLLM manager unavailable.") from e # Stop magic execution

        def _display_status(self, status_info: Dict[str, Any]):
            """Displays a status bar after execution using provided info."""
            duration = status_info.get("duration", 0.0)
            success = status_info.get("success", False)
            tokens_in = status_info.get("tokens_in") # Might be None
            tokens_out = status_info.get("tokens_out") # Might be None
            cost_str = status_info.get("cost_str") # Might be None
            model_used = status_info.get("model_used")

            status_parts = []
            if success:
                status_parts.append(f"✅ Success!")
            else:
                status_parts.append(f"⚠️ Failed!")

            status_parts.append(f"({duration:.2f}s)")

            if model_used:
                 status_parts.append(f"Model: {model_used}")

            token_parts = []
            if tokens_in is not None: token_parts.append(f"In: {tokens_in} tk")
            if tokens_out is not None: token_parts.append(f"Out: {tokens_out} tk")
            if token_parts: status_parts.append(", ".join(token_parts))

            if cost_str: status_parts.append(f"Est. Cost: {cost_str}")

            status_text = " | ".join(status_parts)

            if success:
                bg_color, border_color, text_color = "#e8f5e9", "#a5d6a7", "#1b5e20" # Green tones
            else:
                bg_color, border_color, text_color = "#ffebee", "#ef9a9a", "#c62828" # Red tones

            status_html = f"""
            <div style="background-color: {bg_color}; border: 1px solid {border_color}; color: {text_color};
                        padding: 5px 8px; margin-top: 8px; border-radius: 4px; font-family: sans-serif; font-size: 0.85em; line-height: 1.4;">
                {status_text}
            </div>
            """
            try:
                display(HTML(status_html))
            except Exception as e:
                 logger.warning(f"Failed to display status HTML: {e}")
                 print(f"Status: {status_text}") # Fallback to plain text

        # --- %llm_config Magic ---
        @magic_arguments()
        @argument('-p', '--persona', type=str, help="Select and activate a persona by name.")
        @argument('--show-persona', action='store_true', help="Show the currently active persona details.")
        @argument('--list-personas', action='store_true', help="List available persona names.")
        @argument('--set-override', nargs=2, metavar=('KEY', 'VALUE'), help="Set a temporary LLM param override (e.g., --set-override temperature 0.5).")
        @argument('--remove-override', type=str, metavar='KEY', help="Remove a specific override key.")
        @argument('--clear-overrides', action='store_true', help="Clear all temporary LLM param overrides.")
        @argument('--show-overrides', action='store_true', help="Show the currently active overrides.")
        @argument('--clear-history', action='store_true', help="Clear the current chat history (keeps system prompt).")
        @argument('--save', type=str, nargs='?', const=True, metavar='FILENAME', help="Save session. If no name, uses current session ID. '.md' added automatically.")
        @argument('--load', type=str, metavar='SESSION_ID', help="Load session from specified identifier (filename without .md).")
        @argument('--list-sessions', action='store_true', help="List saved session identifiers.")
        @argument('--list-snippets', action='store_true', help="List available snippet names.")
        @argument('--show-history', action='store_true', help="Display the current message history.")
        @argument('--status', action='store_true', help="Show current status (persona, overrides, history length).")
        @line_magic('llm_config')
        def configure_llm(self, line):
            """Configure the LLM session state and manage resources."""
            try:
                args = parse_argstring(self.configure_llm, line)
                manager = self._get_manager()
            except Exception as e:
                 # Error already printed by _get_manager or parse_argstring
                 return # Stop processing

            action_taken = False # Track if any action was performed

            # --- List Resources ---
            if args.list_personas:
                action_taken = True
                try:
                    personas = manager.list_personas()
                    print("Available Personas:", ", ".join(f"'{p}'" for p in personas) if personas else "None")
                except Exception as e:
                    print(f"❌ Error listing personas: {e}")

            if args.list_snippets:
                action_taken = True
                try:
                    snippets = manager.list_snippets()
                    print("Available Snippets:", ", ".join(f"'{s}'" for s in snippets) if snippets else "None")
                except Exception as e:
                    print(f"❌ Error listing snippets: {e}")

            if args.list_sessions:
                action_taken = True
                try:
                    sessions = manager.list_saved_sessions()
                    print("Saved Sessions:", ", ".join(f"'{s}'" for s in sessions) if sessions else "None")
                except Exception as e:
                    print(f"❌ Error listing saved sessions: {e}")

            # --- Manage Persona ---
            if args.persona:
                action_taken = True
                try:
                    manager.select_persona(args.persona)
                    print(f"✅ Persona activated: '{args.persona}'")
                except ResourceNotFoundError:
                    print(f"❌ Error: Persona '{args.persona}' not found.")
                except Exception as e:
                     print(f"❌ Error setting persona '{args.persona}': {e}")

            # --- Manage Overrides ---
            if args.set_override:
                action_taken = True
                key, value = args.set_override
                # Attempt basic type conversion (optional, could pass strings directly)
                try:
                     # Try float, int, then string
                     parsed_value = float(value) if '.' in value else int(value)
                except ValueError:
                     parsed_value = value # Keep as string if conversion fails
                manager.set_override(key, parsed_value)
                print(f"✅ Override set: {key} = {parsed_value} ({type(parsed_value).__name__})")

            if args.remove_override:
                 action_taken = True
                 key = args.remove_override
                 manager.remove_override(key)
                 print(f"✅ Override removed: {key}")

            if args.clear_overrides:
                action_taken = True
                manager.clear_overrides()
                print("✅ All overrides cleared.")

            # --- Manage History ---
            if args.clear_history:
                action_taken = True
                manager.clear_history()
                print("✅ Chat history cleared.")

            # --- Manage Persistence ---
            if args.load:
                action_taken = True
                try:
                    manager.load_session(args.load)
                    print(f"✅ Session loaded from '{args.load}'.")
                except ResourceNotFoundError:
                    print(f"❌ Error: Session '{args.load}' not found.")
                except PersistenceError as e:
                     print(f"❌ Error loading session '{args.load}': {e}")
                except Exception as e:
                     print(f"❌ Unexpected error loading session '{args.load}': {e}")

            # Save needs to be after load/clear etc.
            if args.save:
                action_taken = True
                try:
                    filename = args.save if isinstance(args.save, str) else None
                    save_path = manager.save_session(identifier=filename)
                    print(f"✅ Session saved to '{Path(save_path).name}'.") # Show only filename
                except PersistenceError as e:
                     print(f"❌ Error saving session: {e}")
                except Exception as e:
                     print(f"❌ Unexpected error saving session: {e}")

            # --- Show Status/Info ---
            if args.show_persona:
                 action_taken = True
                 active_persona = manager.get_active_persona()
                 if active_persona:
                      print(f"Active Persona: '{active_persona.name}'")
                      print(f"  System Prompt: {active_persona.system_prompt[:100]}{'...' if len(active_persona.system_prompt)>100 else ''}")
                      print(f"  LLM Params: {active_persona.llm_params}")
                 else:
                      print("Active Persona: None")

            if args.show_overrides:
                 action_taken = True
                 overrides = manager.get_overrides()
                 print("Active Overrides:", overrides if overrides else "None")

            if args.show_history:
                 action_taken = True
                 history = manager.get_history()
                 print(f"--- History ({len(history)} messages) ---")
                 if not history:
                      print("(empty)")
                 else:
                      for i, msg in enumerate(history):
                           print(f"[{i}] {msg.role.upper()}: {msg.content[:150]}{'...' if len(msg.content)>150 else ''}")
                           print(f"    (ID: ...{msg.id[-6:]}, Cell: {msg.cell_id[-8:] if msg.cell_id else 'N/A'}, Exec: {msg.execution_count})")
                 print("--------------------------")

            # Default action or if explicitly requested: show status
            if args.status or not action_taken:
                 active_persona = manager.get_active_persona()
                 overrides = manager.get_overrides()
                 history = manager.get_history()
                 print("--- NotebookLLM Status ---")
                 print(f"Session ID: {manager._session_id}") # Access internal for status
                 print(f"Active Persona: '{active_persona.name}'" if active_persona else "None")
                 print(f"Active Overrides: {overrides if overrides else 'None'}")
                 print(f"History Length: {len(history)} messages")
                 print("--------------------------")

        # --- %%llm Cell Magic ---
        @magic_arguments()
        # Runtime arguments overriding session state for this call only
        @argument('-p', '--persona', type=str, help="Use specific persona for THIS call only.")
        @argument('-m', '--model', type=str, help="Use specific model for THIS call only.")
        @argument('-t', '--temperature', type=float, help="Set temperature for THIS call.")
        @argument('--max-tokens', type=int, dest='max_tokens', help="Set max_tokens for THIS call.")
        # Behavior control arguments
        @argument('--no-history', action='store_false', dest='add_to_history', help="Do not add this exchange to history.")
        @argument('--no-stream', action='store_false', dest='stream', help="Do not stream output (wait for full response).")
        @argument('--no-rollback', action='store_false', dest='auto_rollback', help="Disable auto-rollback check for this cell run.")
        # Snippet arguments
        @argument('--snippet', type=str, action='append', help="Add user snippet content before sending prompt. Can be used multiple times.")
        @argument('--sys-snippet', type=str, action='append', help="Add system snippet content before sending prompt. Can be used multiple times.")
        # Add other common LLM params as needed (e.g., top_p, frequency_penalty)
        @argument('--param', nargs=2, metavar=('KEY', 'VALUE'), action='append', help="Set any other LLM param ad-hoc (e.g., --param top_p 0.9).")
        @cell_magic('llm')
        async def execute_llm(self, line, cell):
            """Send the cell content as a prompt to the LLM, applying arguments."""
            start_time = time.time()
            status_info = {"success": False, "duration": 0.0} # Initialize status dict

            try:
                args = parse_argstring(self.execute_llm, line)
                manager = self._get_manager()
            except Exception as e:
                 status_info["duration"] = time.time() - start_time
                 self._display_status(status_info)
                 return # Stop processing

            prompt = cell.strip()
            if not prompt:
                print("⚠️ LLM prompt is empty, skipping.")
                status_info["duration"] = time.time() - start_time
                self._display_status(status_info)
                return

            # Handle snippets first - add them to history before the user prompt
            try:
                if args.sys_snippet:
                    for name in args.sys_snippet:
                        if not manager.add_snippet(name, role='system'):
                            print(f"⚠️ Warning: Could not add system snippet '{name}'.")
                if args.snippet:
                    for name in args.snippet:
                         if not manager.add_snippet(name, role='user'):
                              print(f"⚠️ Warning: Could not add user snippet '{name}'.")
            except SnippetError as e:
                 print(f"❌ Error adding snippet: {e}")
                 status_info["duration"] = time.time() - start_time
                 self._display_status(status_info)
                 return # Stop if snippet addition fails critically
            except Exception as e:
                 print(f"❌ Unexpected error processing snippets: {e}")
                 status_info["duration"] = time.time() - start_time
                 self._display_status(status_info)
                 return

            # Prepare runtime params and stream handler
            runtime_params = {}
            if args.model: runtime_params['model'] = args.model
            if args.temperature is not None: runtime_params['temperature'] = args.temperature
            if args.max_tokens is not None: runtime_params['max_tokens'] = args.max_tokens
            if args.param:
                 for key, value in args.param:
                      # Attempt type conversion for ad-hoc params
                      try:
                           parsed_value = float(value) if '.' in value else int(value)
                      except ValueError:
                           parsed_value = value # Keep as string
                      runtime_params[key] = parsed_value

            stream_handler = IPythonStreamHandler() if args.stream else None
            assistant_message: Optional[Message] = None

            try:
                assistant_message = await manager.send_message(
                    prompt=prompt,
                    persona_name=args.persona, # Temporary persona if specified
                    stream_handler=stream_handler,
                    add_to_history=args.add_to_history,
                    auto_rollback=args.auto_rollback,
                    **runtime_params
                )
                status_info["success"] = True

                # --- TODO: Extract token counts and cost ---
                # This requires ChatManager to store/return this info from the LLM response
                # Placeholder values:
                tokens_in = assistant_message.metadata.get("token_usage", {}).get("prompt_tokens") if assistant_message else None
                tokens_out = assistant_message.metadata.get("token_usage", {}).get("completion_tokens") if assistant_message else None
                status_info["tokens_in"] = tokens_in
                status_info["tokens_out"] = tokens_out
                status_info["model_used"] = assistant_message.metadata.get("model_used") if assistant_message else runtime_params.get('model') or manager.get_active_persona().llm_params.get('model') # Best guess
                # Cost calculation needs model costs (complex) - Placeholder
                if tokens_in is not None and tokens_out is not None:
                     cost_milli_cents = tokens_in * 0.005 + tokens_out * 0.015 # Example rates
                     status_info["cost_str"] = f"~${cost_milli_cents / 1000:.4f}"

            except NotebookLLMError as e:
                print(f"❌ LLM Error: {e}") # Display user-friendly errors
            except Exception as e:
                print(f"❌ An unexpected error occurred: {e}")
                logger.exception("Unexpected error during %%llm execution.") # Log traceback
            finally:
                status_info["duration"] = time.time() - start_time
                self._display_status(status_info) # Display status bar

            # If not streaming and successful, display the result cleanly
            if not stream_handler and assistant_message and status_info["success"]:
                display(Markdown(f"**Assistant:**\n{assistant_message.content}"))

        # --- TODO: Implement Auto-Magic Transformer ---
        # This requires defining _auto_magic_transformer and registering/unregistering it
        # with ip.input_transformers_cleanup. It's more complex. Need `llm_setup_forever` etc.

else:
    # If IPython is not available, define a placeholder class
    class NotebookLLMMagics:
        def __init__(self, shell=None):
            logger.warning("IPython not found. NotebookLLM magics are disabled.")
        # Add dummy methods if needed to prevent attribute errors elsewhere
        def configure_llm(self, line): pass
        async def execute_llm(self, line, cell): pass

# --- Extension Loading ---

def load_ipython_extension(ipython):
    """Registers the magics with the IPython runtime."""
    if not _IPYTHON_AVAILABLE:
        print("IPython is not available. Cannot load NotebookLLM magics.", file=sys.stderr)
        return
    try:
        ipython.register_magics(NotebookLLMMagics)
        print("✅ NotebookLLM Magics loaded. Use %llm_config and %%llm.")
        # Optionally display initial status
        # get_chat_manager().status() # Needs a status method or call configure_llm("")
    except Exception as e:
         logger.exception("Failed to register NotebookLLM magics.")
         print(f"❌ Failed to load NotebookLLM Magics: {e}", file=sys.stderr)

def unload_ipython_extension(ipython):
    """Unregisters the magics (optional but good practice)."""
    if not _IPYTHON_AVAILABLE:
        return
    # Magics are typically not explicitly unloaded, but possible if needed.
    # Check if NotebookLLMMagics is registered before trying to unregister
    # if NotebookLLMMagics in ipython.magics_manager.registry:
    #     ipython.magics_manager.unregister(NotebookLLMMagics)
    #     print("NotebookLLM Magics unloaded.")
    # For simplicity, often omitted. Kernel restart achieves the same.
    logger.info("NotebookLLM extension unload requested (typically no action needed).")

