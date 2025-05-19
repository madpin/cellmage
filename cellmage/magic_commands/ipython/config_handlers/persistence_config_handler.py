"""
Persistence configuration handler for the %llm_config magic command.

This module handles session persistence arguments for the %llm_config magic command.
"""

import logging
import os
from typing import Any

from cellmage.exceptions import ResourceNotFoundError

from .base_config_handler import BaseConfigHandler

# Create a logger
logger = logging.getLogger(__name__)


class PersistenceConfigHandler(BaseConfigHandler):
    """Handler for session persistence configuration arguments."""

    def handle_args(self, args: Any, manager: Any) -> bool:
        """
        Handle persistence-related arguments for the %llm_config magic.

        Args:
            args: The parsed arguments from the magic command.
            manager: The ChatManager instance.

        Returns:
            bool: True if any persistence-related action was performed, False otherwise.
        """
        action_taken = False

        # Handle saving the current conversation
        if hasattr(args, "save") and args.save is not None:
            action_taken = True
            try:
                # If --save is used without a value, use the session ID
                session_id = args.save if args.save is not True else None

                if hasattr(manager, "save_conversation"):
                    session_id = manager.save_conversation(session_id)
                    method = "save_conversation"
                elif hasattr(manager, "save_session"):
                    session_id = manager.save_session(session_id)
                    method = "save_session"
                else:
                    raise AttributeError("No method found for saving sessions")

                print("══════════════════════════════════════════════════════════")
                print(f"  ✅ Session saved successfully as '{session_id}' using '{method}'")

                # Get conversations directory path to inform the user
                if hasattr(manager, "settings") and hasattr(manager.settings, "conversations_dir"):
                    print(
                        f"  • Saved to: {os.path.join(manager.settings.conversations_dir, session_id)}.md"
                    )
                print("══════════════════════════════════════════════════════════")
            except Exception as e:
                print("══════════════════════════════════════════════════════════")
                print(f"  ❌ Error saving session: {e}")
                print("══════════════════════════════════════════════════════════")

        # Handle loading a conversation
        if hasattr(args, "load") and args.load:
            action_taken = True
            session_id = args.load
            try:
                print("══════════════════════════════════════════════════════════")
                print(f"  🔄 Loading session: {session_id}")

                # Find the right method to use based on what's available
                if hasattr(manager, "load_session"):
                    manager.load_session(session_id)
                    method = "load_session"
                elif hasattr(manager, "load_conversation"):
                    manager.load_conversation(session_id)
                    method = "load_conversation"
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
                        else:
                            print("  • No saved sessions found")
                    except Exception as e:
                        print(f"  ❌ Error listing sessions: {e}")
                print("══════════════════════════════════════════════════════════")
            except Exception as e:
                print(f"  ❌ Error loading session: {e}")
                print("══════════════════════════════════════════════════════════")

        # Handle listing saved sessions
        if hasattr(args, "list_sessions") and args.list_sessions:
            action_taken = True
            try:
                print("══════════════════════════════════════════════════════════")
                print("  📋 Saved Sessions")
                print("══════════════════════════════════════════════════════════")

                # Find the right method to list sessions
                if hasattr(manager, "list_saved_sessions"):
                    sessions = manager.list_saved_sessions()
                    method = "list_saved_sessions"
                elif hasattr(manager, "list_conversations"):
                    sessions = manager.list_conversations()
                    method = "list_conversations"
                else:
                    raise AttributeError("No method found for listing sessions")

                if sessions:
                    for session in sorted(sessions):
                        print(f"  • {session}")
                    print("──────────────────────────────────────────────────────────")
                    print(f"  ℹ️ {len(sessions)} sessions found using '{method}'")
                else:
                    print("  No saved sessions found")

                print("──────────────────────────────────────────────────────────")
                print("  Use: %llm_config --load <session_id> to load a session")
                print("══════════════════════════════════════════════════════════")
            except Exception as e:
                print(f"  ❌ Error listing sessions: {e}")
                print("══════════════════════════════════════════════════════════")

        # Handle auto-save settings
        if hasattr(args, "auto_save") and args.auto_save:
            action_taken = True
            try:
                # Set auto-save to true
                if hasattr(manager, "set_auto_save"):
                    manager.set_auto_save(True)
                elif hasattr(manager, "settings"):
                    manager.settings.auto_save = True
                else:
                    print("  ❌ Unable to set auto_save: no appropriate setting found")
                    print("══════════════════════════════════════════════════════════")
                    return action_taken

                print("══════════════════════════════════════════════════════════")
                print("  ✅ Auto-save enabled")

                # Show the conversations directory
                conversations_dir = None
                if hasattr(manager, "settings") and hasattr(manager.settings, "conversations_dir"):
                    conversations_dir = manager.settings.conversations_dir
                elif hasattr(manager, "conversations_dir"):
                    conversations_dir = manager.conversations_dir

                if conversations_dir:
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
                print("══════════════════════════════════════════════════════════")
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

        # Handle disabling auto-save
        if hasattr(args, "no_auto_save") and args.no_auto_save:
            action_taken = True
            try:
                # Set auto-save to false
                if hasattr(manager, "set_auto_save"):
                    manager.set_auto_save(False)
                elif hasattr(manager, "settings"):
                    manager.settings.auto_save = False
                else:
                    print("  ❌ Unable to disable auto_save: no appropriate setting found")
                    return action_taken

                print("══════════════════════════════════════════════════════════")
                print("  ✅ Auto-save disabled")
                print("══════════════════════════════════════════════════════════")
            except Exception as e:
                print("══════════════════════════════════════════════════════════")
                print(f"  ❌ Error disabling auto-save: {e}")
                print("══════════════════════════════════════════════════════════")

        return action_taken
