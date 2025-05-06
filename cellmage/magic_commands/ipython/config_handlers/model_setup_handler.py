"""
Model setup handler for the %llm_config magic command.

This module handles model-related arguments for the %llm_config magic command.
"""

import logging
from typing import Any

from .base_config_handler import BaseConfigHandler

# Create a logger
logger = logging.getLogger(__name__)


class ModelSetupHandler(BaseConfigHandler):
    """Handler for model setup configuration arguments."""

    def handle_args(self, args: Any, manager: Any) -> bool:
        """
        Handle model-related arguments for the %llm_config magic.

        Args:
            args: The parsed arguments from the magic command.
            manager: The ChatManager instance.

        Returns:
            bool: True if any model-related action was performed, False otherwise.
        """
        action_taken = False

        if hasattr(args, "model") and args.model:
            action_taken = True
            model_name = args.model
            manager.set_override("model", model_name)

            # Get model mapping information if available
            mapped_model = None
            if hasattr(manager.llm_client, "model_mapper"):
                try:
                    mapped_model = manager.llm_client.model_mapper.resolve_model_name(model_name)
                except Exception:
                    pass

            print("══════════════════════════════════════════════════════════")
            print("  🤖 Model Set")
            print("══════════════════════════════════════════════════════════")
            print(f"  • Model: {model_name}")

            if mapped_model and mapped_model != model_name:
                print(f"  • Maps to: {mapped_model}")

            print("══════════════════════════════════════════════════════════")

        if hasattr(args, "list_mappings") and args.list_mappings:
            action_taken = True

            print("══════════════════════════════════════════════════════════")
            print("  🔄 Model Name Mappings")
            print("══════════════════════════════════════════════════════════")

            has_mappings = False
            if hasattr(manager.llm_client, "model_mapper"):
                try:
                    mappings = manager.llm_client.model_mapper.get_mappings()
                    if mappings:
                        for alias, full_name in mappings.items():
                            print(f"  • {alias} → {full_name}")
                        has_mappings = True
                except Exception as e:
                    print(f"  ❌ Error retrieving mappings: {e}")

            if not has_mappings:
                print("  No model mappings configured")
                print("  • Use %llm_config --add-mapping ALIAS FULL_NAME to add")

            print("══════════════════════════════════════════════════════════")

        if hasattr(args, "add_mapping") and args.add_mapping:
            action_taken = True
            alias, full_name = args.add_mapping

            if hasattr(manager.llm_client, "model_mapper") and hasattr(
                manager.llm_client.model_mapper, "add_mapping"
            ):
                try:
                    manager.llm_client.model_mapper.add_mapping(alias, full_name)
                    print("══════════════════════════════════════════════════════════")
                    print("  ✅ Model Mapping Added")
                    print("══════════════════════════════════════════════════════════")
                    print(f"  • {alias} → {full_name}")
                    print("══════════════════════════════════════════════════════════")
                except Exception as e:
                    print("══════════════════════════════════════════════════════════")
                    print("  ❌ Error adding model mapping")
                    print(f"  • {e}")
                    print("══════════════════════════════════════════════════════════")
            else:
                print("══════════════════════════════════════════════════════════")
                print("  ❌ Model mapper not available")
                print("══════════════════════════════════════════════════════════")

        if hasattr(args, "remove_mapping") and args.remove_mapping:
            action_taken = True
            alias = args.remove_mapping

            if hasattr(manager.llm_client, "model_mapper") and hasattr(
                manager.llm_client.model_mapper, "remove_mapping"
            ):
                try:
                    removed = manager.llm_client.model_mapper.remove_mapping(alias)
                    print("══════════════════════════════════════════════════════════")
                    if removed:
                        print(f"  ✅ Mapping for '{alias}' removed")
                    else:
                        print(f"  ⚠️ Mapping '{alias}' not found")
                    print("══════════════════════════════════════════════════════════")
                except Exception as e:
                    print("══════════════════════════════════════════════════════════")
                    print("  ❌ Error removing model mapping")
                    print(f"  • {e}")
                    print("══════════════════════════════════════════════════════════")
            else:
                print("══════════════════════════════════════════════════════════")
                print("  ❌ Model mapper not available")
                print("══════════════════════════════════════════════════════════")

        return action_taken
