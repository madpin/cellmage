"""
Override configuration handler for the %llm_config magic command.

This module handles parameter override arguments for the %llm_config magic command.
"""

import logging
from typing import Any

from .base_config_handler import BaseConfigHandler

# Create a logger
logger = logging.getLogger(__name__)


class OverrideConfigHandler(BaseConfigHandler):
    """Handler for parameter override configuration arguments."""

    def handle_args(self, args: Any, manager: Any) -> bool:
        """
        Handle override-related arguments for the %llm_config magic.

        Args:
            args: The parsed arguments from the magic command.
            manager: The ChatManager instance.

        Returns:
            bool: True if any override-related action was performed, False otherwise.
        """
        action_taken = False

        if hasattr(args, "set_override") and args.set_override:
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

        if hasattr(args, "remove_override") and args.remove_override:
            action_taken = True
            key = args.remove_override
            manager.remove_override(key)
            print("══════════════════════════════════════════════════════════")
            print("  ⚙️  Parameter Override Removed")
            print("══════════════════════════════════════════════════════════")
            print(f"  • Parameter: {key}")
            print("══════════════════════════════════════════════════════════")

        if hasattr(args, "clear_overrides") and args.clear_overrides:
            action_taken = True
            manager.clear_overrides()
            print("══════════════════════════════════════════════════════════")
            print("  ⚙️  All Parameter Overrides Cleared")
            print("══════════════════════════════════════════════════════════")

        if hasattr(args, "show_overrides") and args.show_overrides:
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
