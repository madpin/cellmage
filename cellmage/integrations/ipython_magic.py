"""
IPython magic commands for CellMage.

This module provides magic commands for using CellMage in IPython/Jupyter notebooks.
"""

import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, Optional

# IPython imports with fallback handling
try:
    from IPython import get_ipython
    from IPython.core.magic import Magics, cell_magic, line_magic, magics_class
    from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

    # Define dummy decorators if IPython is not installed
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

    class DummyMagics:
        pass  # Dummy base class

    Magics = DummyMagics  # Type alias for compatibility


from ..ambient_mode import (
    disable_ambient_mode,
    enable_ambient_mode,
    is_ambient_mode_enabled,
)

# Project imports
from ..chat_manager import ChatManager
from ..context_providers.ipython_context_provider import get_ipython_context_provider
from ..exceptions import PersistenceError, ResourceNotFoundError
from ..models import Message

# Logging setup
logger = logging.getLogger(__name__)

# --- Global Instance Management ---
_chat_manager_instance: Optional[ChatManager] = None
_initialization_error: Optional[Exception] = None


def _init_default_manager() -> ChatManager:
    """Initializes the default ChatManager instance using default components."""
    global _initialization_error
    try:
        # Import necessary components dynamically only if needed
        from ..config import settings
        from ..resources.file_loader import FileLoader
        from ..storage.sqlite_store import (
            SQLiteStore,  # Import SQLiteStore instead of MarkdownStore
        )

        # Determine which adapter to use
        adapter_type = os.environ.get("CELLMAGE_ADAPTER", "direct").lower()

        logger.info(f"Initializing default ChatManager with adapter type: {adapter_type}")

        # Create default dependencies
        loader = FileLoader(settings.personas_dir, settings.snippets_dir)

        # Use SQLiteStore instead of MarkdownStore as default storage
        store = SQLiteStore()  # Use default path from settings
        logger.info("Using SQLite as default storage backend")

        context_provider = get_ipython_context_provider()

        # Initialize the appropriate LLM client adapter
        from ..interfaces import LLMClientInterface

        llm_client: Optional[LLMClientInterface] = None

        if adapter_type == "langchain":
            try:
                from ..adapters.langchain_client import LangChainAdapter

                llm_client = LangChainAdapter(default_model=settings.default_model)
                logger.info("Using LangChain adapter")
            except ImportError:
                # Fall back to Direct adapter if LangChain is not available
                logger.warning(
                    "LangChain adapter requested but not available. Falling back to Direct adapter."
                )
                from ..adapters.direct_client import DirectLLMAdapter

                llm_client = DirectLLMAdapter(default_model=settings.default_model)
        else:
            # Default case: use Direct adapter
            from ..adapters.direct_client import DirectLLMAdapter

            llm_client = DirectLLMAdapter(default_model=settings.default_model)
            logger.info("Using Direct adapter")

        manager = ChatManager(
            settings=settings,
            llm_client=llm_client,
            persona_loader=loader,
            snippet_provider=loader,
            history_store=store,  # Use SQLite store here
            context_provider=context_provider,
        )
        logger.info("Default ChatManager initialized successfully with SQLite storage.")
        _initialization_error = None  # Clear previous error on success
        return manager
    except Exception as e:
        logger.exception("FATAL: Failed to initialize default NotebookLLM ChatManager.")
        _initialization_error = e  # Store the error
        raise RuntimeError(
            f"NotebookLLM setup failed. Please check configuration and logs. Error: {e}"
        ) from e


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


@magics_class
class NotebookLLMMagics(Magics):
    """IPython magic commands for interacting with CellMage."""

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

    def _get_manager(self) -> ChatManager:
        """Helper to get the manager instance, with clear error handling."""
        if not _IPYTHON_AVAILABLE:
            raise RuntimeError("IPython not available")

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

    def _prepare_runtime_params(self, args) -> Dict[str, Any]:
        """Extract runtime parameters from args and convert to dictionary.

        This builds a dictionary of parameters that can be passed to the LLM client.
        """
        runtime_params = {}

        # Handle simple parameters
        if hasattr(args, "temperature") and args.temperature is not None:
            runtime_params["temperature"] = args.temperature

        if hasattr(args, "max_tokens") and args.max_tokens is not None:
            runtime_params["max_tokens"] = args.max_tokens

        # Handle arbitrary parameters from --param
        if hasattr(args, "param") and args.param:
            for key, value in args.param:
                # Try to convert string values to appropriate types
                try:
                    # First try to convert to int or float if it looks numeric
                    if "." in value:
                        parsed_value = float(value)
                    else:
                        try:
                            parsed_value = int(value)
                        except ValueError:
                            parsed_value = value
                except ValueError:
                    parsed_value = value

                runtime_params[key] = parsed_value

        return runtime_params

    # --- Implementation of persona handling ---
    def _handle_persona_commands(self, args, manager: ChatManager) -> bool:
        """Handle persona-related arguments."""
        action_taken = False

        if args.list_personas:
            action_taken = True
            try:
                personas = manager.list_personas()
                print("══════════════════════════════════════════════════════════")
                print("  👤 Available Personas")
                print("══════════════════════════════════════════════════════════")
                if personas:
                    for persona in sorted(personas):
                        print(f"  • {persona}")
                else:
                    print("  No personas found")
                print("──────────────────────────────────────────────────────────")
                print("  Use: %llm_config --persona <name> to activate a persona")
            except Exception as e:
                print(f"❌ Error listing personas: {e}")

        if args.show_persona:
            action_taken = True
            try:
                active_persona = manager.get_active_persona()
                print("══════════════════════════════════════════════════════════")
                print("  👤 Active Persona Details")
                print("══════════════════════════════════════════════════════════")
                if active_persona:
                    print(f"  📝 Name: {active_persona.name}")
                    print("  📋 System Prompt:")

                    # Format system prompt with nice wrapping for readability
                    system_lines = []
                    remaining = active_persona.system_message
                    while remaining and len(remaining) > 80:
                        split_point = remaining[:80].rfind(" ")
                        if split_point == -1:  # No space found, just cut at 80
                            split_point = 80
                        system_lines.append(remaining[:split_point])
                        remaining = remaining[split_point:].lstrip()
                    if remaining:
                        system_lines.append(remaining)

                    for line in system_lines:
                        print(f"    {line}")

                    if active_persona.config:
                        print("  ⚙️  LLM Parameters:")
                        for k, v in active_persona.config.items():
                            print(f"    • {k}: {v}")
                else:
                    print("  ❌ No active persona")
                    print("  • To set a persona, use: %llm_config --persona <name>")
                    print("  • To list available personas, use: %llm_config --list-personas")
                print("══════════════════════════════════════════════════════════")
            except Exception as e:
                print(f"❌ Error retrieving active persona: {e}")
                print("  Try listing available personas with: %llm_config --list-personas")

        if args.persona:
            action_taken = True
            try:
                manager.set_default_persona(args.persona)
                print("══════════════════════════════════════════════════════════")
                print(f"  👤 Persona '{args.persona}' Activated ✅")

                # Show brief summary of the activated persona
                try:
                    active_persona = manager.get_active_persona()
                    if active_persona and active_persona.system_message:
                        # Show just the beginning of the system message
                        preview = active_persona.system_message[:100].replace("\n", " ")
                        if len(active_persona.system_message) > 100:
                            preview += "..."
                        print(f"  📋 System: {preview}")

                    if active_persona and active_persona.config:
                        params = ", ".join(f"{k}={v}" for k, v in active_persona.config.items())
                        print(f"  ⚙️  Params: {params}")

                except Exception:
                    pass  # If this fails, just skip the extra info

                print("══════════════════════════════════════════════════════════")
                print("  Use %llm_config --show-persona for full details")
            except ResourceNotFoundError:
                print(f"❌ Error: Persona '{args.persona}' not found.")
                # List available personas for convenience
                try:
                    personas = manager.list_personas()
                    if personas:
                        print("  Available personas: " + ", ".join(sorted(personas)))
                except Exception:
                    pass
            except Exception as e:
                print(f"❌ Error setting persona '{args.persona}': {e}")

        return action_taken

    # --- Implementation of snippet handling ---
    def _handle_snippet_commands(self, args, manager: ChatManager) -> bool:
        """Handle snippet-related arguments."""
        action_taken = False

        try:
            if hasattr(args, "sys_snippet") and args.sys_snippet:
                action_taken = True
                # If multiple snippets are being added, show a header
                if len(args.sys_snippet) > 1:
                    print("══════════════════════════════════════════════════════════")
                    print("  📎 Loading System Snippets")
                    print("══════════════════════════════════════════════════════════")

                for name in args.sys_snippet:
                    # Handle quoted paths by removing quotes
                    if (name.startswith('"') and name.endswith('"')) or (
                        name.startswith("'") and name.endswith("'")
                    ):
                        name = name[1:-1]

                    # If single snippet and no header printed yet
                    if len(args.sys_snippet) == 1:
                        print("══════════════════════════════════════════════════════════")
                        print(f"  📎 Loading System Snippet: {name}")
                        print("══════════════════════════════════════════════════════════")

                    if manager.add_snippet(name, role="system"):
                        if len(args.sys_snippet) > 1:
                            print(f"  • ✅ Added: {name}")
                        else:
                            print("  ✅ System snippet loaded successfully")
                            # Try to get a preview of the snippet content
                            try:
                                history = manager.get_history()
                                for msg in reversed(history):
                                    if msg.is_snippet and msg.role == "system":
                                        preview = msg.content.replace("\n", " ")[:100]
                                        if len(msg.content) > 100:
                                            preview += "..."
                                        print(f"  📄 Content: {preview}")
                                        break
                            except Exception:
                                pass  # Skip preview if something goes wrong
                    else:
                        if len(args.sys_snippet) > 1:
                            print(f"  • ❌ Failed to add: {name}")
                        else:
                            print(f"  ❌ Failed to load system snippet: {name}")

            if hasattr(args, "snippet") and args.snippet:
                action_taken = True
                # If multiple snippets are being added, show a header
                if len(args.snippet) > 1:
                    print("══════════════════════════════════════════════════════════")
                    print("  📎 Loading User Snippets")
                    print("══════════════════════════════════════════════════════════")

                for name in args.snippet:
                    # Handle quoted paths by removing quotes
                    if (name.startswith('"') and name.endswith('"')) or (
                        name.startswith("'") and name.endswith("'")
                    ):
                        name = name[1:-1]

                    # If single snippet and no header printed yet
                    if len(args.snippet) == 1:
                        print("══════════════════════════════════════════════════════════")
                        print(f"  📎 Loading User Snippet: {name}")
                        print("══════════════════════════════════════════════════════════")

                    if manager.add_snippet(name, role="user"):
                        if len(args.snippet) > 1:
                            print(f"  • ✅ Added: {name}")
                        else:
                            print("  ✅ User snippet loaded successfully")
                            # Try to get a preview of the snippet content
                            try:
                                history = manager.get_history()
                                for msg in reversed(history):
                                    if msg.is_snippet and msg.role == "user":
                                        preview = msg.content.replace("\n", " ")[:100]
                                        if len(msg.content) > 100:
                                            preview += "..."
                                        print(f"  📄 Content: {preview}")
                                        break
                            except Exception:
                                pass  # Skip preview if something goes wrong
                    else:
                        if len(args.snippet) > 1:
                            print(f"  • ❌ Failed to add: {name}")
                        else:
                            print(f"  ❌ Failed to load user snippet: {name}")

            if args.list_snippets:
                action_taken = True
                try:
                    snippets = manager.list_snippets()
                    print("══════════════════════════════════════════════════════════")
                    print("  📎 Available Snippets")
                    print("══════════════════════════════════════════════════════════")
                    if snippets:
                        for snippet in sorted(snippets):
                            print(f"  • {snippet}")
                    else:
                        print("  No snippets found")
                    print("──────────────────────────────────────────────────────────")
                    print("  Use: %llm_config --snippet <name> to load a user snippet")
                    print("  Use: %llm_config --sys-snippet <name> for system snippets")
                except Exception as e:
                    print(f"❌ Error listing snippets: {e}")
        except Exception as e:
            print(f"❌ Error processing snippets: {e}")

        return action_taken

    # --- Implementation of override handling ---
    def _handle_override_commands(self, args, manager: ChatManager) -> bool:
        """Handle override-related arguments."""
        action_taken = False

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

            # Enhanced message for setting override
            print("══════════════════════════════════════════════════════════")
            print("  ⚙️  Parameter Override Set")
            print("══════════════════════════════════════════════════════════")
            print(f"  • Parameter: {key}")
            print(f"  • Value: {parsed_value}")
            print(f"  • Type: {type(parsed_value).__name__}")

            # Try to get model mapping information if this is a model override
            if key.lower() == "model" and hasattr(manager.llm_client, "model_mapper"):
                try:
                    mapped_model = manager.llm_client.model_mapper.resolve_model_name(
                        str(parsed_value)
                    )
                    if mapped_model != str(parsed_value):
                        print(f"  • Maps to: {mapped_model}")
                except Exception:
                    pass

            print("══════════════════════════════════════════════════════════")

        if args.remove_override:
            action_taken = True
            key = args.remove_override
            manager.remove_override(key)
            print("══════════════════════════════════════════════════════════")
            print("  ⚙️  Parameter Override Removed")
            print("══════════════════════════════════════════════════════════")
            print(f"  • Parameter: {key}")
            print("══════════════════════════════════════════════════════════")

        if args.clear_overrides:
            action_taken = True
            manager.clear_overrides()
            print("══════════════════════════════════════════════════════════")
            print("  ⚙️  All Parameter Overrides Cleared")
            print("══════════════════════════════════════════════════════════")

        if args.show_overrides:
            action_taken = True
            overrides = manager.get_overrides()
            print("══════════════════════════════════════════════════════════")
            print("  ⚙️  Active Parameter Overrides")
            print("══════════════════════════════════════════════════════════")
            if overrides:
                for k, v in overrides.items():
                    # Hide API key for security
                    if k.lower() == "api_key":
                        print(f"  • {k} = [HIDDEN]")
                    else:
                        print(f"  • {k} = {v}")
            else:
                print("  No active overrides")
            print("══════════════════════════════════════════════════════════")

        return action_taken

    # --- Implementation of history handling ---
    def _handle_history_commands(self, args, manager: ChatManager) -> bool:
        """Handle history-related arguments."""
        action_taken = False

        if args.clear_history:
            action_taken = True
            manager.clear_history()
            print("✅ Chat history cleared.")

        if args.show_history:
            action_taken = True
            history = manager.get_history()

            # Calculate total tokens for all messages
            total_tokens_in = 0
            total_tokens_out = 0
            total_tokens = 0

            # Calculate cumulative token counts
            for msg in history:
                if msg.metadata:
                    total_tokens_in += msg.metadata.get("tokens_in", 0)
                    total_tokens_out += msg.metadata.get("tokens_out", 0)
                    msg_total = msg.metadata.get("total_tokens", 0)
                    if msg_total > 0:
                        total_tokens += msg_total

            # If no total_tokens were found, calculate from in+out
            if total_tokens == 0:
                total_tokens = total_tokens_in + total_tokens_out

            # Print history header with summary information
            print("📜 Conversation History")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"• Messages: {len(history)}")

            # Format token information
            token_summary = f"• 📊 Total: {total_tokens} tokens"
            if total_tokens_in > 0 or total_tokens_out > 0:
                token_summary += f" (Input: {total_tokens_in} • Output: {total_tokens_out})"
            print(token_summary)

            if not history:
                print("(No messages in history)")
            else:
                # First, display a summary of models used in the conversation
                models_used = {}
                for msg in history:
                    if msg.metadata and "model_used" in msg.metadata:
                        model = msg.metadata.get("model_used", "")
                        if model:
                            models_used[model] = models_used.get(model, 0) + 1

                if models_used:
                    model_str = "• 🤖 Models: " + ", ".join(
                        f"{model} ({count})" for model, count in models_used.items()
                    )
                    print(model_str)

                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                # Display the messages with improved formatting
                for i, msg in enumerate(history):
                    # Get metadata values with defaults
                    tokens_in = msg.metadata.get("tokens_in", 0) if msg.metadata else 0
                    tokens_out = msg.metadata.get("tokens_out", 0) if msg.metadata else 0
                    model_used = msg.metadata.get("model_used", "") if msg.metadata else ""
                    cost_str = msg.metadata.get("cost_str", "") if msg.metadata else ""

                    # Determine role icon and create a formatted role label
                    role_icon = ""
                    if msg.role == "system":
                        role_icon = "⚙️"
                    elif msg.role == "user":
                        role_icon = "👤"
                    elif msg.role == "assistant":
                        role_icon = "🤖"
                    else:
                        role_icon = "📄"

                    role_label = f"[{i}] {role_icon} {msg.role.upper()}"

                    # Display token info based on role
                    token_info = ""
                    if msg.role == "user" and tokens_in > 0:
                        token_info = f"📥 {tokens_in} tokens"
                    elif msg.role == "assistant" and tokens_out > 0:
                        token_info = f"📤 {tokens_out} tokens"
                        if cost_str:
                            token_info += f" • {cost_str}"

                    # Print the message header with role and tokens
                    if token_info:
                        print(f"{role_label}  {token_info}")
                    else:
                        print(role_label)

                    # Format the message content with proper handling of long text
                    content_preview = msg.content.replace("\n", " ").strip()
                    if len(content_preview) > 100:
                        content_preview = content_preview[:97] + "..."
                    print(f"  {content_preview}")

                    # Format metadata in a cleaner way
                    meta_items = []
                    if msg.id:
                        meta_items.append(f"ID: ...{msg.id[-6:]}")
                    if msg.cell_id:
                        meta_items.append(f"Cell: {msg.cell_id[-8:]}")
                    if msg.execution_count:
                        meta_items.append(f"Exec: {msg.execution_count}")
                    if model_used and msg.role == "assistant":
                        meta_items.append(f"Model: {model_used}")
                    if msg.is_snippet:
                        meta_items.append("Snippet: Yes")

                    if meta_items:
                        meta_str = "  └─ " + ", ".join(meta_items)
                        print(meta_str)

                    # Add separator between messages
                    if i < len(history) - 1:
                        print("  ·····")

                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return action_taken

    # --- Implementation of persistence handling ---
    def _handle_persistence_commands(self, args, manager: ChatManager) -> bool:
        """Handle persistence-related arguments."""
        action_taken = False

        if args.list_sessions:
            action_taken = True
            try:
                # Check which method is available for listing sessions
                sessions = []
                method_used = None

                if hasattr(manager, "list_saved_sessions"):
                    sessions = manager.list_saved_sessions()
                    method_used = "list_saved_sessions"
                elif hasattr(manager, "list_conversations"):
                    sessions = manager.list_conversations()
                    method_used = "list_conversations"
                elif hasattr(manager, "history_manager") and hasattr(
                    manager.history_manager, "list_saved_conversations"
                ):
                    sessions = manager.history_manager.list_saved_conversations()
                    method_used = "history_manager.list_saved_conversations"
                else:
                    raise AttributeError(
                        "No method found for listing sessions. Make sure a conversations directory exists."
                    )

                # Format the output in a user-friendly way
                print("══════════════════════════════════════════════════════════")
                print("  📋 Saved Sessions")
                print("══════════════════════════════════════════════════════════")

                if sessions:
                    for session in sorted(sessions):
                        print(f"  • {session}")
                    print("──────────────────────────────────────────────────────────")
                    print(f"  Total: {len(sessions)} session(s)")
                    print("  Use: %llm_config --load SESSION_NAME to load a session")
                else:
                    print("  No saved sessions found.")
                    if hasattr(manager, "settings") and hasattr(
                        manager.settings, "conversations_dir"
                    ):
                        print(f"  Sessions directory: {manager.settings.conversations_dir}")
                    print("  Use: %llm_config --save SESSION_NAME to save the current conversation")

                print("══════════════════════════════════════════════════════════")
                logger.debug(f"Listed {len(sessions)} sessions using {method_used}")
            except Exception as e:
                print(f"❌ Error listing saved sessions: {e}")
                if hasattr(manager, "settings") and hasattr(manager.settings, "conversations_dir"):
                    conversations_dir = manager.settings.conversations_dir
                    print(f"  Please make sure the directory exists: {conversations_dir}")
                    # Try to check if the directory exists
                    import os

                    if not os.path.exists(conversations_dir):
                        print(
                            f"  ℹ️ The conversations directory does not exist. Creating it at: {conversations_dir}"
                        )
                        try:
                            os.makedirs(conversations_dir, exist_ok=True)
                            print("  ✅ Created conversations directory successfully.")
                        except Exception as mkdir_error:
                            print(f"  ❌ Failed to create conversations directory: {mkdir_error}")

        # Handle auto-save configuration
        if hasattr(args, "auto_save") and args.auto_save:
            action_taken = True
            try:
                manager.settings.auto_save = True
                # Get absolute path for better user experience
                conversations_dir = os.path.abspath(manager.settings.conversations_dir)
                print("══════════════════════════════════════════════════════════")
                print("  🔄 Auto-Save Enabled")
                print("══════════════════════════════════════════════════════════")
                print(f"  • Conversations will be saved to: {conversations_dir}")

                # Check if directory exists, create if not
                if not os.path.exists(conversations_dir):
                    print("  • Directory doesn't exist, creating it now...")
                    try:
                        os.makedirs(conversations_dir, exist_ok=True)
                        print("  ✅ Directory created successfully.")
                    except Exception as mkdir_error:
                        print(f"  ❌ Failed to create directory: {mkdir_error}")

                print("══════════════════════════════════════════════════════════")
            except Exception as e:
                print(f"❌ Error enabling auto-save: {e}")

        if hasattr(args, "no_auto_save") and args.no_auto_save:
            action_taken = True
            try:
                manager.settings.auto_save = False
                print("══════════════════════════════════════════════════════════")
                print("  🔄 Auto-Save Disabled")
                print("══════════════════════════════════════════════════════════")
                print("  • Conversations will not be saved automatically.")
                print("  • Use %llm_config --save to manually save conversations.")
                print("══════════════════════════════════════════════════════════")
            except Exception as e:
                print(f"❌ Error disabling auto-save: {e}")

        if args.load:
            action_taken = True
            try:
                # Check which method is available for loading sessions
                session_id = args.load

                print("══════════════════════════════════════════════════════════")
                print(f"  📂 Loading Session: {session_id}")
                print("══════════════════════════════════════════════════════════")

                if hasattr(manager, "load_session"):
                    manager.load_session(session_id)
                    method = "load_session"
                elif hasattr(manager, "load_conversation"):
                    manager.load_conversation(session_id)
                    method = "load_conversation"
                elif hasattr(manager, "history_manager") and hasattr(
                    manager.history_manager, "load_conversation"
                ):
                    manager.history_manager.load_conversation(session_id)
                    method = "history_manager.load_conversation"
                else:
                    raise AttributeError("No method found for loading sessions")

                # Try to get history length after loading
                try:
                    history = manager.get_history()
                    print(f"  ✅ Session loaded successfully using '{method}'")
                    print(f"  • Messages: {len(history)}")
                except Exception:
                    print(f"  ✅ Session loaded successfully using '{method}'")

                print("══════════════════════════════════════════════════════════")

            except ResourceNotFoundError:
                print(f"  ❌ Session '{session_id}' not found.")
                # Try to list available sessions for user convenience
                if hasattr(manager, "list_saved_sessions") or hasattr(
                    manager, "list_conversations"
                ):
                    print("  Available sessions:")
                    try:
                        if hasattr(manager, "list_saved_sessions"):
                            sessions = manager.list_saved_sessions()
                        elif hasattr(manager, "list_conversations"):
                            sessions = manager.list_conversations()

                        # Show up to 5 available sessions
                        if sessions:
                            for i, session in enumerate(sorted(sessions)[:5]):
                                print(f"  • {session}")
                            if len(sessions) > 5:
                                print(f"  • ... and {len(sessions) - 5} more")
                    except Exception:
                        pass
                print("══════════════════════════════════════════════════════════")
            except PersistenceError as e:
                print(f"  ❌ Error loading session: {e}")
                print("══════════════════════════════════════════════════════════")
            except Exception as e:
                print(f"  ❌ Unexpected error: {e}")
                print("══════════════════════════════════════════════════════════")

        # Save needs to be after load/clear etc.
        if args.save:
            action_taken = True
            try:
                from pathlib import Path

                print("══════════════════════════════════════════════════════════")
                print("  💾 Saving Session")
                print("══════════════════════════════════════════════════════════")

                # Convert True to None for default behavior if --save was used without argument
                filename = args.save if isinstance(args.save, str) else None
                if filename is not None:
                    print(f"  • Name: {filename}")

                # Check which method is available for saving sessions
                if hasattr(manager, "save_session"):
                    save_path = manager.save_session(identifier=filename)
                    method = "save_session"
                elif hasattr(manager, "save_conversation"):
                    save_path = manager.save_conversation(filename)
                    method = "save_conversation"
                elif hasattr(manager, "history_manager") and hasattr(
                    manager.history_manager, "save_conversation"
                ):
                    save_path = manager.history_manager.save_conversation(filename)
                    method = "history_manager.save_conversation"
                else:
                    raise AttributeError("No method found for saving sessions")

                # Make the path more user-friendly by showing relative path if inside conversations_dir
                try:
                    if hasattr(manager.settings, "conversations_dir"):
                        conv_dir = Path(manager.settings.conversations_dir).resolve()
                        file_path = Path(save_path).resolve()
                        if str(file_path).startswith(str(conv_dir)):
                            # Show path relative to conversations_dir
                            rel_path = file_path.relative_to(conv_dir)
                            display_path = f"{conv_dir.name}/{rel_path}"
                        else:
                            display_path = str(file_path)
                    else:
                        display_path = save_path
                except Exception:
                    # Fallback to just the filename if the above fails
                    display_path = Path(save_path).name

                print(f"  ✅ Session saved successfully using '{method}'")
                print(f"  • Path: {display_path}")
                print("══════════════════════════════════════════════════════════")

            except PersistenceError as e:
                print(f"  ❌ Error saving session: {e}")
                print("══════════════════════════════════════════════════════════")
            except Exception as e:
                print(f"  ❌ Unexpected error: {e}")
                # Check if conversations directory exists
                if hasattr(manager, "settings") and hasattr(manager.settings, "conversations_dir"):
                    if not os.path.exists(manager.settings.conversations_dir):
                        print(
                            f"  The conversations directory does not exist: {manager.settings.conversations_dir}"
                        )
                        print(
                            "  Try creating it manually or use %llm_config --auto-save to create it automatically."
                        )
                print("══════════════════════════════════════════════════════════")

        return action_taken

    # --- Implementation of model setting ---
    def _handle_model_setting(self, args, manager: ChatManager) -> bool:
        """Handle model setting and mapping configuration."""
        action_taken = False

        if hasattr(args, "model") and args.model:
            action_taken = True
            if manager.llm_client is not None:
                manager.llm_client.set_override("model", args.model)
                logger.info(f"Setting default model to: {args.model}")
                print(f"✅ Default model set to: {args.model}")
            else:
                print("⚠️ Could not set model: LLM client not found or doesn't support overrides")

        if hasattr(args, "list_mappings") and args.list_mappings:
            action_taken = True
            if (
                manager.llm_client is not None
                and hasattr(manager.llm_client, "model_mapper")
                and manager.llm_client.model_mapper is not None
            ):
                mappings = manager.llm_client.model_mapper.get_mappings()
                if mappings:
                    print("\nCurrent model mappings:")
                    for alias, full_name in sorted(mappings.items()):
                        print(f"  {alias:<10} -> {full_name}")
                else:
                    print("\nNo model mappings configured")
            else:
                print("⚠️ Model mapping not available")

        if hasattr(args, "add_mapping") and args.add_mapping:
            action_taken = True
            if manager.llm_client is not None and hasattr(manager.llm_client, "model_mapper"):
                alias, full_name = args.add_mapping
                manager.llm_client.model_mapper.add_mapping(alias, full_name)
                print(f"✅ Added mapping: {alias} -> {full_name}")
            else:
                print("⚠️ Model mapping not available")

        if hasattr(args, "remove_mapping") and args.remove_mapping:
            action_taken = True
            if hasattr(manager.llm_client, "model_mapper"):
                if manager.llm_client.model_mapper.remove_mapping(args.remove_mapping):
                    print(f"✅ Removed mapping for: {args.remove_mapping}")
                else:
                    print(f"⚠️ No mapping found for: {args.remove_mapping}")
            else:
                print("⚠️ Model mapping not available")

        return action_taken

    # --- Implementation of adapter switching ---
    def _handle_adapter_switch(self, args, manager: ChatManager) -> bool:
        """Handle adapter switching."""
        action_taken = False

        if hasattr(args, "adapter") and args.adapter:
            action_taken = True
            adapter_type = args.adapter.lower()

            try:
                # Import necessary components dynamically
                from ..config import settings

                # Initialize the appropriate LLM client adapter
                if adapter_type == "langchain":
                    try:
                        from ..adapters.langchain_client import LangChainAdapter
                        from ..interfaces import LLMClientInterface

                        # Create new adapter instance with current settings from existing client
                        current_api_key = None
                        current_api_base = None
                        current_model = settings.default_model

                        if manager.llm_client:
                            if hasattr(manager.llm_client, "get_overrides"):
                                overrides = manager.llm_client.get_overrides()
                                current_api_key = overrides.get("api_key")
                                current_api_base = overrides.get("api_base")
                                current_model = overrides.get("model", current_model)

                        # Create the new adapter
                        new_client: LLMClientInterface = LangChainAdapter(
                            api_key=current_api_key,
                            api_base=current_api_base,
                            default_model=current_model,
                        )

                        # Set the new adapter
                        manager.llm_client = new_client

                        # Update env var for persistence between sessions
                        os.environ["CELLMAGE_ADAPTER"] = "langchain"

                        print("✅ Switched to LangChain adapter")
                        logger.info("Switched to LangChain adapter")

                    except ImportError:
                        print(
                            "❌ LangChain adapter not available. Make sure langchain is installed."
                        )
                        logger.error("LangChain adapter requested but not available")

                elif adapter_type == "direct":
                    from ..adapters.direct_client import DirectLLMAdapter

                    # Create new adapter instance with current settings from existing client
                    current_api_key = None
                    current_api_base = None
                    current_model = settings.default_model

                    if manager.llm_client:
                        if hasattr(manager.llm_client, "get_overrides"):
                            overrides = manager.llm_client.get_overrides()
                            current_api_key = overrides.get("api_key")
                            current_api_base = overrides.get("api_base")
                            current_model = overrides.get("model", current_model)

                    # Create the new adapter
                    new_client = DirectLLMAdapter(
                        api_key=current_api_key,
                        api_base=current_api_base,
                        default_model=current_model,
                    )

                    # Set the new adapter
                    manager.llm_client = new_client

                    # Update env var for persistence between sessions
                    os.environ["CELLMAGE_ADAPTER"] = "direct"

                    print("✅ Switched to Direct adapter")
                    logger.info("Switched to Direct adapter")

                else:
                    print(f"❌ Unknown adapter type: {adapter_type}")
                    logger.error(f"Unknown adapter type requested: {adapter_type}")

            except Exception as e:
                print(f"❌ Error switching adapter: {e}")
                logger.exception(f"Error switching to adapter {adapter_type}: {e}")

        return action_taken

    # --- Implementation of status display ---
    def _show_status(self, manager: ChatManager) -> None:
        """Show current status information."""
        active_persona = manager.get_active_persona()
        overrides = manager.get_overrides()
        history = manager.get_history()

        # Calculate token statistics
        total_tokens_in = 0
        total_tokens_out = 0
        total_tokens = 0
        models_used = {}

        for msg in history:
            if msg.metadata:
                tokens_in = msg.metadata.get("tokens_in", 0)
                tokens_out = msg.metadata.get("tokens_out", 0)
                total_tokens_in += tokens_in
                total_tokens_out += tokens_out
                msg_total = msg.metadata.get("total_tokens", 0)
                if msg_total > 0:
                    total_tokens += msg_total

                # Track models used
                model = msg.metadata.get("model_used", "")
                if model and msg.role == "assistant":
                    models_used[model] = models_used.get(model, 0) + 1

        # If no total_tokens were calculated from metadata, use in+out sum
        if total_tokens == 0:
            total_tokens = total_tokens_in + total_tokens_out

        # Get session information
        session_id = getattr(manager, "_session_id", "Unknown")
        adapter_type = os.environ.get("CELLMAGE_ADAPTER", "direct").lower()
        is_ambient = is_ambient_mode_enabled()

        # Get API base URL if available
        api_base = None
        if hasattr(manager, "llm_client") and hasattr(manager.llm_client, "get_overrides"):
            client_overrides = manager.llm_client.get_overrides()
            api_base = client_overrides.get("api_base")
        if not api_base and "OPENAI_API_BASE" in os.environ:
            api_base = os.environ.get("OPENAI_API_BASE")

        # Get model information
        current_model = None
        mapped_model = None
        if hasattr(manager, "llm_client"):
            if hasattr(manager.llm_client, "get_overrides"):
                client_overrides = manager.llm_client.get_overrides()
                current_model = client_overrides.get("model")

            # Get model mapping information if available
            if hasattr(manager.llm_client, "model_mapper") and current_model:
                if hasattr(manager.llm_client.model_mapper, "resolve_model_name"):
                    mapped_model = manager.llm_client.model_mapper.resolve_model_name(current_model)
                    # If they're the same, no mapping is applied
                    if mapped_model == current_model:
                        mapped_model = None

        # Get storage information
        storage_type = "Unknown"
        storage_location = "Unknown"
        if hasattr(manager, "history_manager"):
            if hasattr(manager.history_manager, "store"):
                store = manager.history_manager.store
                store_class_name = store.__class__.__name__

                if store_class_name == "SQLiteStore":
                    storage_type = "SQLite"
                    if hasattr(store, "db_path"):
                        storage_location = str(store.db_path)
                elif store_class_name == "MarkdownStore":
                    storage_type = "Markdown"
                    if hasattr(store, "save_dir"):
                        storage_location = str(store.save_dir)
                elif store_class_name == "MemoryStore":
                    storage_type = "Memory (no persistence)"
                    storage_location = "In-memory only"

        # Print simplified status output with dividers but no side borders
        print("══════════════════════════════════════════════════════════")
        print("  🪄 CellMage Status Summary                             ")
        print("══════════════════════════════════════════════════════════")

        # Session information
        print(f"  📌 Session ID: {session_id}")
        print(f"  🤖 LLM Adapter: {adapter_type.capitalize()}")
        if api_base:
            print(f"  🔗 API Base URL: {api_base}")
        if current_model:
            print(f"  📝 Current Model: {current_model}")
            if mapped_model:
                print(f"      → Maps to: {mapped_model}")
        print(f"  🔄 Ambient Mode: {'✅ Active' if is_ambient else '❌ Disabled'}")

        # Persona information
        print("──────────────────────────────────────────────────────────")
        print("  👤 Persona")
        if active_persona:
            print(f"    • Name: {active_persona.name}")
            # Truncate system prompt if too long
            sys_prompt = active_persona.system_message
            if sys_prompt:
                if len(sys_prompt) > 70:
                    sys_prompt = sys_prompt[:67] + "..."
                print(f"    • System: {sys_prompt}")

            # Show persona parameters if available
            if active_persona.config:
                param_str = ", ".join(f"{k}={v}" for k, v in active_persona.config.items())
                if len(param_str) > 70:
                    param_str = param_str[:67] + "..."
                print(f"    • Parameters: {param_str}")
        else:
            print("    • No active persona")

        # Parameter overrides
        print("──────────────────────────────────────────────────────────")
        print("  ⚙️  Parameter Overrides")
        if overrides:
            for k, v in overrides.items():
                # Skip displaying API key for security
                if k.lower() == "api_key":
                    print(f"    • {k} = [HIDDEN]")
                else:
                    print(f"    • {k} = {v}")
        else:
            print("    • No active overrides")

        # History information
        print("──────────────────────────────────────────────────────────")
        print("  📜 Conversation History")
        print(f"    • Messages: {len(history)}")

        # Show storage information
        print(f"    • Storage Type: {storage_type}")
        print(f"    • Storage Location: {storage_location}")

        # Show token counts
        if total_tokens > 0:
            print(f"    • Total Tokens: {total_tokens:,}")
            if total_tokens_in > 0 or total_tokens_out > 0:
                print(f"      - Input: {total_tokens_in:,}")
                print(f"      - Output: {total_tokens_out:,}")

        # Show models used
        if models_used:
            print("    • Models Used:")
            for model, count in models_used.items():
                print(f"      - {model}: {count} responses")

        # Integrations status
        print("──────────────────────────────────────────────────────────")
        print("  🔌 Integrations")

        # Check for Jira integration
        try:
            import sys

            jira_available = "cellmage.integrations.jira_magic" in sys.modules
            print(f"    • Jira: {'✅ Loaded' if jira_available else '❌ Not loaded'}")
        except Exception:
            print("    • Jira: ❓ Unknown")

        # Check for GitLab integration
        try:
            gitlab_available = "cellmage.integrations.gitlab_magic" in sys.modules
            print(f"    • GitLab: {'✅ Loaded' if gitlab_available else '❌ Not loaded'}")
        except Exception:
            print("    • GitLab: ❓ Unknown")

        # Check for GitHub integration
        try:
            github_available = "cellmage.integrations.github_magic" in sys.modules
            print(f"    • GitHub: {'✅ Loaded' if github_available else '❌ Not loaded'}")
        except Exception:
            print("    • GitHub: ❓ Unknown")

        # Check for Confluence integration
        try:
            confluence_available = "cellmage.integrations.confluence_magic" in sys.modules
            print(f"    • Confluence: {'✅ Loaded' if confluence_available else '❌ Not loaded'}")
        except Exception:
            print("    • Confluence: ❓ Unknown")

        # Show environment/config file paths
        print("──────────────────────────────────────────────────────────")
        print("  📁 Configuration")
        if hasattr(manager, "settings"):
            if hasattr(manager.settings, "personas_dir"):
                print(f"    • Personas Dir: {manager.settings.personas_dir}")
            if hasattr(manager.settings, "snippets_dir"):
                print(f"    • Snippets Dir: {manager.settings.snippets_dir}")
            if hasattr(manager.settings, "conversations_dir"):
                print(f"    • Save Dir: {manager.settings.conversations_dir}")
            if hasattr(manager.settings, "auto_save"):
                print(
                    f"    • Auto-Save: {'✅ Enabled' if manager.settings.auto_save else '❌ Disabled'}"
                )

        print("══════════════════════════════════════════════════════════")

        # Add hint for more details
        print("\nℹ️  For more details:")
        print("  • %llm_config --show-persona (detailed persona info)")
        print("  • %llm_config --show-history (full conversation history)")
        print("  • %llm_config --show-overrides (all parameter overrides)")
        print("  • %llm_config --list-mappings (view model name mappings)")

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

        # Handle different types of commands
        action_taken |= self._handle_model_setting(args, manager)
        action_taken |= self._handle_snippet_commands(args, manager)
        action_taken |= self._handle_persona_commands(args, manager)
        action_taken |= self._handle_override_commands(args, manager)
        action_taken |= self._handle_history_commands(args, manager)
        action_taken |= self._handle_persistence_commands(args, manager)
        action_taken |= self._handle_adapter_switch(args, manager)

        # Default action or if explicitly requested: show status
        if args.status or not action_taken:
            self._show_status(manager)

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
        # First, apply all the regular llm_config settings
        args = parse_argstring(self.configure_llm_persistent, line)

        try:
            manager = self._get_manager()
        except Exception as e:
            print(f"Error getting manager: {e}")
            return  # Stop processing

        # Track if any action was performed
        action_taken = False

        # Handle different types of commands
        action_taken |= self._handle_model_setting(args, manager)
        action_taken |= self._handle_snippet_commands(args, manager)
        action_taken |= self._handle_persona_commands(args, manager)
        action_taken |= self._handle_override_commands(args, manager)
        action_taken |= self._handle_history_commands(args, manager)
        action_taken |= self._handle_persistence_commands(args, manager)

        # Default action or if explicitly requested: show status
        if args.status or not action_taken:
            self._show_status(manager)

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

    @magic_arguments()
    @argument("-p", "--persona", type=str, help="Use specific persona for THIS call only.")
    @argument("-m", "--model", type=str, help="Use specific model for THIS call only.")
    @argument("-t", "--temperature", type=float, help="Set temperature for THIS call.")
    @argument("--max-tokens", type=int, dest="max_tokens", help="Set max_tokens for THIS call.")
    @argument(
        "--no-history",
        action="store_false",
        dest="add_to_history",
        help="Do not add this exchange to history.",
    )
    @argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        help="Do not stream output (wait for full response).",
    )
    @argument(
        "--no-rollback",
        action="store_false",
        dest="auto_rollback",
        help="Disable auto-rollback check for this cell run.",
    )
    @argument(
        "--param",
        nargs=2,
        metavar=("KEY", "VALUE"),
        action="append",
        help="Set any other LLM param ad-hoc (e.g., --param top_p 0.9).",
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
    @cell_magic("llm")
    def execute_llm(self, line, cell):
        """Send the cell content as a prompt to the LLM, applying arguments."""
        if not _IPYTHON_AVAILABLE:
            return

        start_time = time.time()
        status_info = {"success": False, "duration": 0.0}
        context_provider = get_ipython_context_provider()

        try:
            args = parse_argstring(self.execute_llm, line)
            manager = self._get_manager()
        except Exception as e:
            print(f"Error parsing arguments: {e}")
            status_info["duration"] = time.time() - start_time
            context_provider.display_status(status_info)
            return

        # Check if the persona exists if one was specified
        temp_persona = None
        if args.persona:
            # Check if persona exists
            logger.info(f"DEBUG: Checking for persona '{args.persona}'")
            if manager.persona_loader and manager.persona_loader.get_persona(args.persona):
                temp_persona = manager.persona_loader.get_persona(args.persona)
                print(f"Using persona: {args.persona} for this request only")
                logger.info(f"DEBUG: Successfully loaded persona '{args.persona}'")

                # If using an external persona (starts with / or .), ensure its system message is added
                # and it's the first system message
                if (
                    args.persona.startswith("/") or args.persona.startswith(".")
                ) and temp_persona.system_message:
                    logger.info(f"Using external file persona: {args.persona}")

                    # Get current history
                    current_history = manager.history_manager.get_history()

                    # Extract system and non-system messages
                    system_messages = [m for m in current_history if m.role == "system"]
                    non_system_messages = [m for m in current_history if m.role != "system"]

                    # Clear the history
                    manager.history_manager.clear_history(keep_system=False)

                    # Add persona system message first
                    manager.history_manager.add_message(
                        Message(
                            role="system", content=temp_persona.system_message, id=str(uuid.uuid4())
                        )
                    )

                    # Re-add all existing system messages
                    for msg in system_messages:
                        manager.history_manager.add_message(msg)

                    # Re-add all non-system messages
                    for msg in non_system_messages:
                        manager.history_manager.add_message(msg)
            else:
                # If persona not found, log available personas and warn the user
                available_personas = (
                    manager.list_personas() if hasattr(manager, "list_personas") else []
                )
                logger.info(f"DEBUG: Available personas: {available_personas}")
                print(f"❌ Error: Persona '{args.persona}' not found.")
                print("  To list available personas, use: %llm_config --list-personas")
                status_info["duration"] = time.time() - start_time
                context_provider.display_status(status_info)
                return

        # Rest of the method remains the same
        prompt = cell.strip()
        if not prompt:
            print("⚠️ LLM prompt is empty, skipping.")
            status_info["duration"] = time.time() - start_time
            context_provider.display_status(status_info)
            return

        # Handle snippets
        try:
            self._handle_snippet_commands(args, manager)
        except Exception as e:
            print(f"❌ Unexpected error processing snippets: {e}")
            status_info["duration"] = time.time() - start_time
            context_provider.display_status(status_info)
            return

        # Prepare runtime params
        runtime_params = self._prepare_runtime_params(args)

        # Handle model override
        original_model = None
        if args.model:
            # Directly set model override in the LLM client to ensure highest priority
            if (
                hasattr(manager, "llm_client")
                and manager.llm_client is not None
                and hasattr(manager.llm_client, "set_override")
            ):
                # Temporarily set model override for this call
                original_model = manager.llm_client.get_overrides().get("model")
                manager.llm_client.set_override("model", args.model)
                logger.debug(f"Temporarily set model override to: {args.model}")
            else:
                # Fallback if direct override not possible
                runtime_params["model"] = args.model

        # Debug logging
        logger.debug(f"Sending message with prompt: '{prompt[:50]}...'")
        logger.debug(f"Runtime params: {runtime_params}")

        try:
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
            if (
                args.model
                and hasattr(manager, "llm_client")
                and hasattr(manager.llm_client, "set_override")
            ):
                if original_model is not None:
                    manager.llm_client.set_override("model", original_model)
                    logger.debug(f"Restored original model override: {original_model}")
                else:
                    manager.llm_client.remove_override("model")
                    logger.debug("Removed temporary model override")

            # If result is successful, mark as success and collect status info
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
            print(f"❌ LLM Error: {e}")
            logger.error(f"Error during LLM call: {e}")
            # Add error message to status_info for copying
            status_info["response_content"] = f"Error: {str(e)}"

            # Make sure to restore model override even on error
            if (
                args.model
                and hasattr(manager, "llm_client")
                and hasattr(manager.llm_client, "set_override")
            ):
                if original_model is not None:
                    manager.llm_client.set_override("model", original_model)
                else:
                    manager.llm_client.remove_override("model")
                logger.debug("Restored model override after error")
        finally:
            status_info["duration"] = time.time() - start_time
            # Always display status bar
            context_provider.display_status(status_info)

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


# --- Extension Loading ---
def load_ipython_extension(ipython):
    """
    Registers the magics with the IPython runtime.

    By default, this now loads the SQLite-backed implementation for improved
    conversation management. For legacy file-based storage, set the
    CELLMAGE_USE_FILE_STORAGE=1 environment variable.
    """
    if not _IPYTHON_AVAILABLE:
        print("IPython is not available. Cannot load extension.", file=sys.stderr)
        return

    # Check if we should use legacy file-based storage
    use_file_storage = os.environ.get("CELLMAGE_USE_FILE_STORAGE", "0") == "1"

    if not use_file_storage:
        # Use the SQLite implementation by default
        try:
            from .sqlite_magic import load_ipython_extension as load_sqlite

            # Forward to SQLite extension loader
            load_sqlite(ipython)
            logger.info("Loaded SQLite-backed CellMage extension (default)")

            # Verify magic commands are registered
            if "%llm_config" not in ipython.magic_manager.magics["line"]:
                logger.warning(
                    "llm_config magic not found after loading SQLite extension, registering directly"
                )
                magic_class = NotebookLLMMagics(ipython)
                ipython.register_magics(magic_class)

            return
        except ImportError:
            logger.warning("SQLite storage not available, falling back to file-based storage")
            print(
                "⚠️ SQLite storage not available, falling back to file-based storage",
                file=sys.stderr,
            )
            use_file_storage = True
        except Exception as e:
            logger.error(f"Error loading SQLite extension: {e}")
            print(f"⚠️ Error loading SQLite extension: {e}", file=sys.stderr)
            print("Falling back to file-based storage", file=sys.stderr)
            use_file_storage = True

    # Legacy file-based implementation (only used if specifically requested or if SQLite fails)
    if use_file_storage:
        try:
            # Register the magic class with IPython
            magic_class = NotebookLLMMagics(ipython)
            ipython.register_magics(magic_class)
            logger.info("Legacy file-based CellMage extension loaded successfully")
            print("ℹ️ Legacy file-based CellMage extension loaded", file=sys.stderr)

            # Verify magic commands are registered
            if "%llm_config" not in ipython.magic_manager.magics["line"]:
                logger.warning("llm_config magic not registered properly, attempting to fix")
                ipython.register_magics(magic_class)

        except Exception as e:
            logger.exception("Failed to register CellMage magics.")
            print(f"❌ Failed to initialize NotebookLLM: {e}", file=sys.stderr)


def unload_ipython_extension(ipython):
    """Unregisters the magics (optional but good practice)."""
    if not _IPYTHON_AVAILABLE:
        return
    logger.info("Unload requested (typically no action needed).")
