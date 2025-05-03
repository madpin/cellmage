"""
Core magic commands for CellMage.

This module provides the core IPython magic commands for CellMage.
"""

import logging
import os
import sys
import time
from typing import Any, Dict

# IPython imports with fallback handling
try:
    from IPython.core.magic import Magics, cell_magic, line_magic, magics_class
    from IPython.core.magic_arguments import argument, magic_arguments

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

from ..chat_manager import ChatManager
from ..context_providers.ipython_context_provider import get_ipython_context_provider

# Logging setup
logger = logging.getLogger(__name__)


def prepare_runtime_params(args) -> Dict[str, Any]:
    """
    Extract runtime parameters from args and convert to dictionary.

    Args:
        args: The parsed argument namespace

    Returns:
        Dictionary of parameters that can be passed to the LLM client
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


def handle_snippet_commands(args, manager: ChatManager) -> bool:
    """
    Handle snippet-related arguments.

    Args:
        args: The parsed argument namespace
        manager: Chat manager instance

    Returns:
        True if any action was taken, False otherwise
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


def handle_model_setting(args, manager: ChatManager) -> bool:
    """
    Handle model setting and mapping configuration.

    Args:
        args: The parsed argument namespace
        manager: Chat manager instance

    Returns:
        True if any action was taken, False otherwise
    """
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


def handle_adapter_switch(args, manager: ChatManager) -> bool:
    """
    Handle adapter switching.

    Args:
        args: The parsed argument namespace
        manager: Chat manager instance

    Returns:
        True if any action was taken, False otherwise
    """
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
                    print("❌ LangChain adapter not available. Make sure langchain is installed.")
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


def process_cell_as_prompt(manager: ChatManager, cell_content: str) -> None:
    """
    Process a regular code cell as an LLM prompt in ambient mode.

    Args:
        manager: Chat manager instance
        cell_content: Content of the cell to process
    """
    if not _IPYTHON_AVAILABLE:
        return

    start_time = time.time()
    status_info = {"success": False, "duration": 0.0}
    context_provider = get_ipython_context_provider()

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


# Function to get the ChatManager instance
def get_chat_manager_instance():
    """
    Get the ChatManager instance, with proper error handling.

    Returns:
        ChatManager instance or None on error
    """
    if not _IPYTHON_AVAILABLE:
        print("❌ IPython not available", file=sys.stderr)
        return None

    try:
        # Import from ipython_magic to maintain compatibility
        from ..integrations.ipython_magic import get_chat_manager

        return get_chat_manager()
    except Exception as e:
        print("❌ NotebookLLM Error: Could not get Chat Manager.", file=sys.stderr)
        print(f"   Reason: {e}", file=sys.stderr)
        print(
            "   Please check your configuration (.env file, API keys, directories) and restart the kernel.",
            file=sys.stderr,
        )
        return None
