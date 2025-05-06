"""
Snippet configuration handler for the %llm_config magic command.

This module handles snippet-related arguments for the %llm_config magic command.
"""

import logging
from typing import Any

from .base_config_handler import BaseConfigHandler

# Create a logger
logger = logging.getLogger(__name__)


class SnippetConfigHandler(BaseConfigHandler):
    """Handler for snippet-related configuration arguments."""

    def handle_args(self, args: Any, manager: Any) -> bool:
        """
        Handle snippet-related arguments for the %llm_config magic.

        Args:
            args: The parsed arguments from the magic command.
            manager: The ChatManager instance.

        Returns:
            bool: True if any snippet-related action was performed, False otherwise.
        """
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

            if hasattr(args, "list_snippets") and args.list_snippets:
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
