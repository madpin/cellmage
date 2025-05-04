"""
Configuration magic commands for CellMage.

This module provides the %llm_config line magic for configuring LLM interactions.
"""

import os

from IPython.core.magic import line_magic, magics_class
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

from ...exceptions import PersistenceError, ResourceNotFoundError
from .common import IPythonMagicsBase, logger


@magics_class
class ConfigMagics(IPythonMagicsBase):
    """Configuration magic commands for CellMage.

    Provides the %llm_config line magic for configuring LLM settings,
    personas, snippets, model overrides, and history management.
    """

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

    # --- Implementation of persona handling ---
    def _handle_persona_commands(self, args, manager) -> bool:
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
                print("  Use: %llm_config --persona <n> to activate a persona")
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
                    print("  • To set a persona, use: %llm_config --persona <n>")
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
    def _handle_snippet_commands(self, args, manager) -> bool:
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
                    print("  Use: %llm_config --snippet <n> to load a user snippet")
                    print("  Use: %llm_config --sys-snippet <n> for system snippets")
                except Exception as e:
                    print(f"❌ Error listing snippets: {e}")
        except Exception as e:
            print(f"❌ Error processing snippets: {e}")

        return action_taken

    # --- Implementation of override handling ---
    def _handle_override_commands(self, args, manager) -> bool:
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
    def _handle_history_commands(self, args, manager) -> bool:
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
    def _handle_persistence_commands(self, args, manager) -> bool:
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
    def _handle_model_setting(self, args, manager) -> bool:
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
    def _handle_adapter_switch(self, args, manager) -> bool:
        """Handle adapter switching."""
        action_taken = False

        if hasattr(args, "adapter") and args.adapter:
            action_taken = True
            adapter_type = args.adapter.lower()

            try:
                # Import necessary components dynamically
                from ...config import settings

                # Initialize the appropriate LLM client adapter
                if adapter_type == "langchain":
                    try:
                        from ...adapters.langchain_client import LangChainAdapter
                        from ...interfaces import LLMClientInterface

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
                    from ...adapters.direct_client import DirectLLMAdapter

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
    def _show_status(self, manager):
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

        # Check ambient mode status
        try:
            from ...ambient_mode import is_ambient_mode_enabled

            is_ambient = is_ambient_mode_enabled()
        except ImportError:
            is_ambient = False

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
