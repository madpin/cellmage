"""
Adapter configuration handler for the %llm_config magic command.

This module handles adapter-related arguments for the %llm_config magic command.
"""

import logging
import os
from typing import Any

from cellmage.adapters.direct_client import DirectLLMAdapter
from cellmage.adapters.langchain_client import LangChainAdapter
from cellmage.config import settings
from cellmage.interfaces import LLMClientInterface

from .base_config_handler import BaseConfigHandler

# Create a logger
logger = logging.getLogger(__name__)


class AdapterConfigHandler(BaseConfigHandler):
    """Handler for LLM adapter configuration arguments."""

    def handle_args(self, args: Any, manager: Any) -> bool:
        """
        Handle adapter-related arguments for the %llm_config magic.

        Args:
            args: The parsed arguments from the magic command.
            manager: The ChatManager instance.

        Returns:
            bool: True if any adapter-related action was performed, False otherwise.
        """
        action_taken = False

        if hasattr(args, "adapter") and args.adapter:
            action_taken = True
            adapter_type = args.adapter.lower()

            try:
                # Initialize the appropriate LLM client adapter
                if adapter_type == "langchain":
                    try:
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
