# --- Imports ---
import sys
import time
import logging
import os  # Added for handling file paths
from pathlib import Path  # Added for handling file paths
from typing import Optional, Tuple, Dict, Any

try:
    from IPython import get_ipython
    from IPython.core.magic import Magics, line_magic, cell_magic, magics_class
    from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring, argument_group
    from IPython.display import display, Markdown, HTML, update_display

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

    # Define dummy decorators if IPython is not installed, so the file can still be imported
    # This allows checking functionality even without IPython (e.g., basic linting)
    def magics_class(cls):
        return cls

    def line_magic(func):
        return func

    def cell_magic(func):
        return func

    def magic_arguments():
        return lambda func: func

    def argument(*args, **kwargs):
        return lambda func: func

    class Magics:
        pass  # Dummy base class


# --- Project Imports ---
# Use absolute imports relative to the package root
from ..chat_manager import ChatManager
from ..interfaces import ContextProvider
from ..exceptions import (
    NotebookLLMError,
    ResourceNotFoundError,
    ConfigurationError,
    LLMInteractionError,
    PersistenceError,
)
from ..models import Message  # For type hints if needed

# --- Logging ---
logger = logging.getLogger(__name__)

# --- Global Instance Management ---
# Global instance (or factory-created) - needs careful management in IPython
# A function to get/create the manager instance is generally safer.
_chat_manager_instance: Optional[ChatManager] = None
_initialization_error: Optional[Exception] = None
_ambient_mode_enabled: bool = False  # Flag to track if ambient mode is active


# --- Cell Transformer Function ---
def _auto_process_cells(lines):
    """
    Input transformer that processes regular code cells as LLM prompts.
    This transformer is registered when ambient mode is enabled.
    """
    if not lines or not _ambient_mode_enabled:
        return lines  # Empty cell or ambient mode disabled

    # Don't transform cells that start with a magic command
    first_line_stripped = lines[0].lstrip()
    if first_line_stripped.startswith("%") or first_line_stripped.startswith("!"):
        return lines

    # Get the cell content
    cell_content = "\n".join(lines)

    # Use this specialized code to safely handle the transformation
    new_lines = [
        f"""
try:
    import sys
    from IPython import get_ipython
    
    # Get the registered magic instance
    ip_shell = get_ipython()
    magics_instance = ip_shell.magics_manager.registry.get('NotebookLLMMagics')
    
    if magics_instance and hasattr(magics_instance, "_process_cell_as_prompt"):
        # Process the cell content as a prompt
        magics_instance._process_cell_as_prompt({repr(cell_content)})
    else:
        print("Error: Could not find NotebookLLMMagics instance or _process_cell_as_prompt method.", file=sys.stderr)
except Exception as e:
    import sys
    print(f"Error during ambient mode processing: {{e}}", file=sys.stderr)
"""
    ]
    return new_lines


def _init_default_manager() -> ChatManager:
    """Initializes the default ChatManager instance using default components."""
    global _initialization_error
    try:
        # Import necessary components dynamically only if needed
        from ..config import settings
        from ..adapters.direct_client import DirectLLMAdapter
        from ..resources.file_loader import FileLoader  # Default file-based loaders
        from ..storage.markdown_store import MarkdownStore  # Default markdown store

        logger.info("Initializing default ChatManager components...")

        # Create default dependencies
        loader = FileLoader(settings.personas_dir, settings.snippets_dir)
        store = MarkdownStore(settings.save_dir)
        client = DirectLLMAdapter(default_model=settings.default_model)  # Relies on settings/env vars
        context_provider = IPythonContextProvider()  # Provide IPython context

        manager = ChatManager(
            settings=settings,
            llm_client=client,
            persona_loader=loader,
            snippet_provider=loader,
            history_store=store,
            context_provider=context_provider,
        )
        logger.info("Default ChatManager initialized successfully.")
        _initialization_error = None  # Clear previous error on success
        return manager
    except Exception as e:
        logger.exception("FATAL: Failed to initialize default NotebookLLM ChatManager.")
        _initialization_error = e  # Store the error
        raise RuntimeError(f"NotebookLLM setup failed. Please check configuration and logs. Error: {e}") from e


def get_chat_manager() -> ChatManager:
    """Gets or creates the singleton ChatManager instance."""
    global _chat_manager_instance
    if _chat_manager_instance is None:
        if _initialization_error:
            raise RuntimeError(
                f"NotebookLLM previously failed to initialize: {_initialization_error}"
            ) from _initialization_error
        logger.debug("ChatManager instance not found, attempting initialization.")
        _chat_manager_instance = _init_default_manager()

    return _chat_manager_instance


# --- IPython Specific Implementations ---


class IPythonContextProvider(ContextProvider):
    """
    Provides execution context from IPython/Jupyter environments.

    Handles cell IDs, execution counts, and displaying responses.
    """

    _POTENTIAL_CELL_ID_KEYS = ["cellId", "vscode_cell_id", "google_colab_cell_id", "metadata"]

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
                return exec_count, cell_id

            if hasattr(ipython, "execution_count"):
                exec_count = ipython.execution_count

            if (
                hasattr(ipython, "kernel")
                and hasattr(ipython.kernel, "shell")
                and hasattr(ipython.kernel.shell, "parent_header")
                and isinstance(ipython.kernel.shell.parent_header, dict)
            ):
                metadata = ipython.kernel.shell.parent_header.get("metadata", {})
                search_pools = [ipython.kernel.shell.parent_header, metadata]

                if isinstance(metadata.get("metadata"), dict):
                    search_pools.append(metadata["metadata"])
                if isinstance(metadata.get("colab"), dict):
                    search_pools.append(metadata["colab"])

                found_id = False
                for pool in search_pools:
                    if not isinstance(pool, dict):
                        continue

                    for key in self._POTENTIAL_CELL_ID_KEYS:
                        potential_id = pool.get(key)
                        if isinstance(potential_id, str) and potential_id:
                            cell_id = potential_id
                            found_id = True
                            break

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
                print(content)
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
                print(f"Assistant:\n{content}")
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
                # Initialize with empty content, we'll accumulate the full text
                return {
                    "display_obj": display(Markdown("**Assistant:**\n"), display_id=True),
                    "accumulated_content": "",
                }
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
                # Accumulate content instead of replacing it
                if isinstance(display_object, dict) and "accumulated_content" in display_object:
                    # Add new content to accumulated content
                    display_object["accumulated_content"] += content
                    # Update the display with the full accumulated content
                    display_object["display_obj"].update(
                        Markdown(f"**Assistant:**\n{display_object['accumulated_content']}")
                    )
                else:
                    # Fallback for older format display objects
                    print(content, end="", flush=True)
            except Exception as e:
                self.logger.error(f"Error updating stream display: {e}")
                print(content, end="", flush=True)
        else:
            print(content, end="", flush=True)

    def display_status(
        self,
        success: bool,
        duration: float,
        tokens_in: int,
        tokens_out: int,
        cost_mili_cents: int,
        model: Optional[str] = None,
    ) -> None:
        """
        Display a status bar with information about the LLM call.
        This is called from the chat_manager.py when direct calls are made.
        Forwards to the internal minimal display implementation.
        """
        # Convert parameters to match _display_status format
        status_info = {
            "success": success,
            "duration": duration,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "model_used": model,
        }

        # Calculate cost string in consistent format
        if cost_mili_cents is not None and cost_mili_cents > 0:
            if cost_mili_cents < 1000:  # Less than 1 cent
                status_info["cost_str"] = f"{cost_mili_cents / 1000:.4f}¢"
            elif cost_mili_cents < 100000:  # Less than $1
                status_info["cost_str"] = f"{cost_mili_cents / 1000:.2f}¢"
            else:  # $1 or more
                status_info["cost_str"] = f"${cost_mili_cents / 100000:.2f}"

        # Use the unified status display implementation
        self._display_status(status_info)

    def _display_status(self, status_info: Dict[str, Any]):
        """Displays a minimal status bar after execution using provided info."""
        if not _IPYTHON_AVAILABLE:
            return

        duration = status_info.get("duration", 0.0)
        success = status_info.get("success", False)
        tokens_in = status_info.get("tokens_in")
        tokens_out = status_info.get("tokens_out")
        cost_str = status_info.get("cost_str")
        model_used = status_info.get("model_used")

        # Create a more compact status display
        icon = "✓" if success else "⚠"
        model_text = f" {model_used}" if model_used else ""
        tokens_text = ""
        if tokens_in is not None or tokens_out is not None:
            in_txt = f"{tokens_in}↓" if tokens_in is not None else "?"
            out_txt = f"{tokens_out}↑" if tokens_out is not None else "?"
            tokens_text = f" • {in_txt}/{out_txt} tokens"

        cost_text = f" • ${cost_str}" if cost_str else ""

        # Single unified status text
        status_text = f"{icon}{model_text} • {duration:.2f}s{tokens_text}{cost_text}"

        # More subtle styling with smaller text and lighter colors
        if success:
            bg_color, text_color = "#f1f8e9", "#33691e"  # Light green bg, dark green text
            border_color = "#c5e1a5"  # Light green border
        else:
            bg_color, text_color = "#ffebee", "#c62828"  # Light red bg, darker red text
            border_color = "#ef9a9a"  # Light red border

        status_html = f"""
        <div style="background-color: {bg_color}; border: 1px solid {border_color}; color: {text_color};
                    padding: 3px 6px; margin-top: 4px; border-radius: 3px; font-family: monospace; 
                    font-size: 0.75em; line-height: 1.2; display: inline-block; opacity: 0.85;">
            {status_text}
        </div>
        """
        try:
            # Use a single display call to avoid duplicates
            display(HTML(status_html))
        except Exception:
            # Fallback if display fails
            print(f"Status: {status_text}")


# --- Magic Class ---


@magics_class
class NotebookLLMMagics(Magics):
    """IPython Magics for interacting with the NotebookLLM ChatManager."""

    def __init__(self, shell):
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not found. NotebookLLM magics are disabled.")
            return

        super().__init__(shell)
        try:
            get_chat_manager()
            logger.info("NotebookLLMMagics initialized and ChatManager accessed successfully.")
        except Exception as e:
            logger.error(f"Error initializing NotebookLLM during magic setup: {e}")

    def _process_cell_as_prompt(self, cell_content: str):
        """
        Process a regular code cell as an LLM prompt in ambient mode.
        This method is called by the _auto_process_cells transformer.
        """
        if not _IPYTHON_AVAILABLE:
            return

        start_time = time.time()
        status_info = {"success": False, "duration": 0.0}

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
                try:
                    history = manager.history_manager.get_history()
                    if len(history) >= 2:
                        status_info["tokens_in"] = history[-2].metadata.get("tokens_in")
                    if len(history) >= 1:
                        status_info["tokens_out"] = history[-1].metadata.get("tokens_out")
                        status_info["cost_str"] = history[-1].metadata.get("cost_str")
                        status_info["model_used"] = history[-1].metadata.get("model_used")
                except Exception as e:
                    logger.warning(f"Error retrieving status info from history in ambient mode: {e}")

        except Exception as e:
            print(f"❌ LLM Error (Ambient Mode): {e}", file=sys.stderr)
            logger.error(f"Error during LLM call in ambient mode: {e}")
        finally:
            status_info["duration"] = time.time() - start_time
            # Display status bar
            self._display_status(status_info)

    def _get_manager(self) -> ChatManager:
        """Helper to get the manager instance, raising clearly if initialization failed."""
        if not _IPYTHON_AVAILABLE:
            return None

        try:
            return get_chat_manager()
        except Exception as e:
            print("❌ NotebookLLM Error: Could not get Chat Manager.", file=sys.stderr)
            print(f"   Reason: {e}", file=sys.stderr)
            print(
                "   Please check your configuration (.env file, API keys, directories) and restart the kernel.",
                file=sys.stderr,
            )
            raise RuntimeError("NotebookLLM manager unavailable.") from e

    def _display_status(self, status_info: Dict[str, Any]):
        """Displays a minimal status bar after execution using provided info."""
        if not _IPYTHON_AVAILABLE:
            return

        duration = status_info.get("duration", 0.0)
        success = status_info.get("success", False)
        tokens_in = status_info.get("tokens_in")
        tokens_out = status_info.get("tokens_out")
        cost_str = status_info.get("cost_str")
        model_used = status_info.get("model_used")

        # Create a more compact status display
        icon = "✓" if success else "⚠"
        model_text = f" {model_used}" if model_used else ""
        tokens_text = ""
        if tokens_in is not None or tokens_out is not None:
            in_txt = f"{tokens_in}↓" if tokens_in is not None else "?"
            out_txt = f"{tokens_out}↑" if tokens_out is not None else "?"
            tokens_text = f" • {in_txt}/{out_txt} tokens"

        cost_text = f" • ${cost_str}" if cost_str else ""

        # Single unified status text
        status_text = f"{icon}{model_text} • {duration:.2f}s{tokens_text}{cost_text}"

        # More subtle styling with smaller text and lighter colors
        if success:
            bg_color, text_color = "#f1f8e9", "#33691e"  # Light green bg, dark green text
            border_color = "#c5e1a5"  # Light green border
        else:
            bg_color, text_color = "#ffebee", "#c62828"  # Light red bg, darker red text
            border_color = "#ef9a9a"  # Light red border

        status_html = f"""
        <div style="background-color: {bg_color}; border: 1px solid {border_color}; color: {text_color};
                    padding: 3px 6px; margin-top: 4px; border-radius: 3px; font-family: monospace; 
                    font-size: 0.75em; line-height: 1.2; display: inline-block; opacity: 0.85;">
            {status_text}
        </div>
        """
        try:
            # Use a single display call to avoid duplicates
            display(HTML(status_html))
        except Exception:
            # Fallback if display fails
            print(f"Status: {status_text}")

    @magic_arguments()
    @argument("-p", "--persona", type=str, help="Select and activate a persona by name.")
    @argument("--show-persona", action="store_true", help="Show the currently active persona details.")
    @argument("--list-personas", action="store_true", help="List available persona names.")
    @argument(
        "--set-override",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Set a temporary LLM param override (e.g., --set-override temperature 0.5).",
    )
    @argument("--remove-override", type=str, metavar="KEY", help="Remove a specific override key.")
    @argument("--clear-overrides", action="store_true", help="Clear all temporary LLM param overrides.")
    @argument("--show-overrides", action="store_true", help="Show the currently active overrides.")
    @argument("--clear-history", action="store_true", help="Clear the current chat history (keeps system prompt).")
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
    @argument("--show-history", action="store_true", help="Display the current message history.")
    @argument("--status", action="store_true", help="Show current status (persona, overrides, history length).")
    @argument("--model", type=str, help="Set the default model for the LLM client.")
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
    @line_magic("llm_config")
    def configure_llm(self, line):
        """Configure the LLM session state and manage resources."""
        try:
            args = parse_argstring(self.configure_llm, line)
            manager = self._get_manager()
        except Exception as e:
            # Error already printed by _get_manager or parse_argstring
            return  # Stop processing

        action_taken = False  # Track if any action was performed

        # --- Handle model setting specifically ---
        # We need to ensure model is properly set on the LLM client
        if hasattr(args, "model") and args.model:
            action_taken = True
            if hasattr(manager, "llm_client") and hasattr(manager.llm_client, "set_override"):
                manager.llm_client.set_override("model", args.model)
                logger.info(f"Setting default model to: {args.model}")
                print(f"✅ Default model set to: {args.model}")
            else:
                print(f"⚠️ Could not set model: LLM client not found or doesn't support overrides")

        # --- Handle snippets ---
        try:
            if hasattr(args, "sys_snippet") and args.sys_snippet:
                action_taken = True
                for name in args.sys_snippet:
                    if manager.add_snippet(name, role="system"):
                        print(f"✅ Added system snippet: '{name}'")
                    else:
                        print(f"⚠️ Warning: Could not add system snippet '{name}'.")
            
            if hasattr(args, "snippet") and args.snippet:
                action_taken = True
                for name in args.snippet:
                    if manager.add_snippet(name, role="user"):
                        print(f"✅ Added user snippet: '{name}'")
                    else:
                        print(f"⚠️ Warning: Could not add user snippet '{name}'.")
        except Exception as e:
            print(f"❌ Error processing snippets: {e}")

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
                manager.set_default_persona(args.persona)  # Changed from select_persona to set_default_persona
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
                parsed_value = float(value) if "." in value else int(value)
            except ValueError:
                parsed_value = value  # Keep as string if conversion fails
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
                print(f"✅ Session saved to '{Path(save_path).name}'.")  # Show only filename
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
                print(
                    f"  System Prompt: {active_persona.system_message[:100]}{'...' if len(active_persona.system_message) > 100 else ''}"
                )
                print(f"  LLM Params: {active_persona.config}")
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
                    print(
                        f"[{i}] {msg.role.upper()}: {msg.content[:150]}{'...' if len(msg.content) > 150 else ''}"
                    )
                    print(
                        f"    (ID: ...{msg.id[-6:]}, Cell: {msg.cell_id[-8:] if msg.cell_id else 'N/A'}, Exec: {msg.execution_count})"
                    )
            print("--------------------------")

        # Default action or if explicitly requested: show status
        if args.status or not action_taken:
            active_persona = manager.get_active_persona()
            overrides = manager.get_overrides()
            history = manager.get_history()
            print("--- NotebookLLM Status ---")
            print(f"Session ID: {manager._session_id}")  # Access internal for status
            print(f"Active Persona: '{active_persona.name}'" if active_persona else "None")
            print(f"Active Overrides: {overrides if overrides else 'None'}")
            print(f"History Length: {len(history)} messages")
            print("--------------------------")

    @magic_arguments()
    @argument("-p", "--persona", type=str, help="Select and activate a persona by name.")
    @argument("--show-persona", action="store_true", help="Show the currently active persona details.")
    @argument("--list-personas", action="store_true", help="List available persona names.")
    @argument(
        "--set-override",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Set a temporary LLM param override (e.g., --set-override temperature 0.5).",
    )
    @argument("--remove-override", type=str, metavar="KEY", help="Remove a specific override key.")
    @argument("--clear-overrides", action="store_true", help="Clear all temporary LLM param overrides.")
    @argument("--show-overrides", action="store_true", help="Show the currently active overrides.")
    @argument("--clear-history", action="store_true", help="Clear the current chat history (keeps system prompt).")
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
    @argument("--show-history", action="store_true", help="Display the current message history.")
    @argument("--status", action="store_true", help="Show current status (persona, overrides, history length).")
    @argument("--model", type=str, help="Set the default model for the LLM client.")
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
    @line_magic("llm_config_persistent")
    def configure_llm_persistent(self, line):
        """
        Configure the LLM session state and activate ambient mode.

        This magic command has the same functionality as %llm_config but also
        enables 'ambient mode', which processes all regular code cells as LLM prompts.
        Use %disable_llm_config_persistent to turn off ambient mode.
        """
        global _ambient_mode_enabled

        # First, apply all the regular llm_config settings
        self.configure_llm(line)

        # Then enable ambient mode by registering the cell transformer
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython not available. Cannot enable ambient mode.", file=sys.stderr)
            return

        ip = get_ipython()
        if not ip:
            print("❌ IPython shell not found. Cannot enable ambient mode.", file=sys.stderr)
            return

        # Register the transformer if it's not already registered
        transformer_func = _auto_process_cells

        # Register with input_transformers_cleanup for better compatibility
        transformer_list = ip.input_transformers_cleanup
        if transformer_func not in transformer_list:
            transformer_list.append(transformer_func)
            _ambient_mode_enabled = True
            print(
                "✅ Ambient mode ENABLED. All cells will now be processed as LLM prompts unless they start with % or !."
            )
            print("   Run %disable_llm_config_persistent to disable ambient mode.")
        else:
            print("ℹ️ Ambient mode is already active.")

    @line_magic("disable_llm_config_persistent")
    def disable_llm_config_persistent(self, line):
        """Deactivate ambient mode (stops processing regular code cells as LLM prompts)."""
        global _ambient_mode_enabled

        if not _IPYTHON_AVAILABLE:
            print("❌ IPython not available.", file=sys.stderr)
            return

        ip = get_ipython()
        if not ip:
            print("❌ IPython shell not found.", file=sys.stderr)
            return

        transformer_func = _auto_process_cells
        transformer_list = ip.input_transformers_cleanup

        try:
            # Remove all instances just in case it was added multiple times
            while transformer_func in transformer_list:
                transformer_list.remove(transformer_func)

            _ambient_mode_enabled = False
            print("❌ Ambient mode DISABLED. Regular cells will now be executed normally.")
        except ValueError:
            print("ℹ️ Ambient mode was not active.")

        return None

    @magic_arguments()
    @argument("-p", "--persona", type=str, help="Use specific persona for THIS call only.")
    @argument("-m", "--model", type=str, help="Use specific model for THIS call only.")
    @argument("-t", "--temperature", type=float, help="Set temperature for THIS call.")
    @argument("--max-tokens", type=int, dest="max_tokens", help="Set max_tokens for THIS call.")
    @argument(
        "--no-history", action="store_false", dest="add_to_history", help="Do not add this exchange to history."
    )
    @argument(
        "--no-stream", action="store_false", dest="stream", help="Do not stream output (wait for full response)."
    )
    @argument(
        "--no-rollback",
        action="store_false",
        dest="auto_rollback",
        help="Disable auto-rollback check for this cell run.",
    )
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
        "--param",
        nargs=2,
        metavar=("KEY", "VALUE"),
        action="append",
        help="Set any other LLM param ad-hoc (e.g., --param top_p 0.9).",
    )
    @cell_magic("llm")
    def execute_llm(self, line, cell):
        """Send the cell content as a prompt to the LLM, applying arguments."""
        if not _IPYTHON_AVAILABLE:
            return

        start_time = time.time()
        status_info = {"success": False, "duration": 0.0}

        # The problem is here - we're skipping the status display too aggressively
        # Set to False initially, we'll conditionally set it to True only when needed
        skip_status_display = False

        try:
            args = parse_argstring(self.execute_llm, line)
            manager = self._get_manager()
        except Exception as e:
            print(f"Error parsing arguments: {e}")
            status_info["duration"] = time.time() - start_time
            self._display_status(status_info)
            return

        prompt = cell.strip()
        if not prompt:
            print("⚠️ LLM prompt is empty, skipping.")
            status_info["duration"] = time.time() - start_time
            self._display_status(status_info)
            return

        # Handle snippets
        try:
            if args.sys_snippet:
                for name in args.sys_snippet:
                    if not manager.add_snippet(name, role="system"):
                        print(f"⚠️ Warning: Could not add system snippet '{name}'.")
            if args.snippet:
                for name in args.snippet:
                    if not manager.add_snippet(name, role="user"):
                        print(f"⚠️ Warning: Could not add user snippet '{name}'.")
        except Exception as e:
            print(f"❌ Unexpected error processing snippets: {e}")
            status_info["duration"] = time.time() - start_time
            self._display_status(status_info)
            return

        # Prepare runtime params
        runtime_params = {}
        if args.model:
            # Directly set model override in the LLM client to ensure highest priority
            if hasattr(manager, "llm_client") and hasattr(manager.llm_client, "set_override"):
                # Temporarily set model override for this call
                original_model = None
                if hasattr(manager.llm_client, "_instance_overrides"):
                    original_model = manager.llm_client._instance_overrides.get("model")
                manager.llm_client.set_override("model", args.model)
                logger.debug(f"Temporarily set model override to: {args.model}")
            else:
                # Fallback if direct override not possible
                runtime_params["model"] = args.model

        if args.temperature is not None:
            runtime_params["temperature"] = args.temperature
        if args.max_tokens is not None:
            runtime_params["max_tokens"] = args.max_tokens
        if args.param:
            for key, value in args.param:
                try:
                    parsed_value = float(value) if "." in value else int(value)
                except ValueError:
                    parsed_value = value
                runtime_params[key] = parsed_value

        # Debug logging
        logger.debug(f"Sending message with prompt: '{prompt[:50]}...'")
        logger.debug(f"Runtime params: {runtime_params}")

        try:
            # Only skip status display if streaming is enabled
            # This was the problem - wrong logic for determining when to skip
            skip_status_display = args.stream and not args.persona

            # Call the ChatManager's chat method
            result = manager.chat(
                prompt=prompt,
                persona_name=args.persona,
                stream=args.stream,
                add_to_history=args.add_to_history,
                auto_rollback=args.auto_rollback,
                **runtime_params,
            )

            # If we temporarily overrode the model, restore the original value
            if args.model and hasattr(manager, "llm_client") and hasattr(manager.llm_client, "set_override"):
                if original_model is not None:
                    manager.llm_client.set_override("model", original_model)
                    logger.debug(f"Restored original model override: {original_model}")
                else:
                    manager.llm_client.remove_override("model")
                    logger.debug("Removed temporary model override")

            # If result is successful, mark as success
            if result:
                status_info["success"] = True
                try:
                    history = manager.history_manager.get_history()
                    if len(history) >= 2:
                        status_info["tokens_in"] = history[-2].metadata.get("tokens_in")
                    if len(history) >= 1:
                        status_info["tokens_out"] = history[-1].metadata.get("tokens_out")
                        status_info["cost_str"] = history[-1].metadata.get("cost_str")
                        status_info["model_used"] = history[-1].metadata.get("model_used")
                except Exception as e:
                    logger.warning(f"Error retrieving status info from history: {e}")

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            logger.error(f"Error during LLM call: {e}")
            skip_status_display = False

            # Make sure to restore model override even on error
            if args.model and hasattr(manager, "llm_client") and hasattr(manager.llm_client, "set_override"):
                if original_model is not None:
                    manager.llm_client.set_override("model", original_model)
                else:
                    manager.llm_client.remove_override("model")
                logger.debug("Restored model override after error")
        finally:
            status_info["duration"] = time.time() - start_time
            # Always display status bar, regardless of mode
            self._display_status(status_info)

        return None


# --- Extension Loading ---
def load_ipython_extension(ipython):
    """Registers the magics with the IPython runtime."""
    if not _IPYTHON_AVAILABLE:
        print("IPython is not available. Cannot load NotebookLLM magics.", file=sys.stderr)
        return
    try:
        magic_class = NotebookLLMMagics(ipython)
        ipython.register_magics(magic_class)
        print("✅ NotebookLLM Magics loaded. Use %llm_config and %%llm.")
        print("   For ambient mode, try %llm_config_persistent to process all cells as LLM prompts.")
    except Exception as e:
        logger.exception("Failed to register NotebookLLM magics.")
        print(f"❌ Failed to load NotebookLLM Magics: {e}", file=sys.stderr)


def unload_ipython_extension(ipython):
    """Unregisters the magics (optional but good practice)."""
    if not _IPYTHON_AVAILABLE:
        return
    logger.info("NotebookLLM extension unload requested (typically no action needed).")
