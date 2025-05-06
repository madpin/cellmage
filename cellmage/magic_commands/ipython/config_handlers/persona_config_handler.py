"""
Persona configuration handler for the %llm_config magic command.

This module handles persona-related arguments for the %llm_config magic command.
"""

import logging
from typing import Any

from cellmage.exceptions import ResourceNotFoundError

from .base_config_handler import BaseConfigHandler

# Create a logger
logger = logging.getLogger(__name__)


class PersonaConfigHandler(BaseConfigHandler):
    """Handler for persona-related configuration arguments."""

    def handle_args(self, args: Any, manager: Any) -> bool:
        """
        Handle persona-related arguments for the %llm_config magic.

        Args:
            args: The parsed arguments from the magic command.
            manager: The ChatManager instance.

        Returns:
            bool: True if any persona-related action was performed, False otherwise.
        """
        action_taken = False

        if hasattr(args, "list_personas") and args.list_personas:
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

        if hasattr(args, "show_persona") and args.show_persona:
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

        if hasattr(args, "persona") and args.persona:
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
