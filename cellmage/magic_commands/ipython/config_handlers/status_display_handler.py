"""
Status display handler for the %llm_config magic command.

This module handles the status display for the %llm_config magic command.
"""

import logging
import os
import sys
from typing import Any

from cellmage.ambient_mode import is_ambient_mode_enabled
from cellmage.magic_commands.core import extract_metadata_for_status
from cellmage.utils.token_utils import count_tokens

from .base_config_handler import BaseConfigHandler

# Create a logger
logger = logging.getLogger(__name__)


class StatusDisplayHandler(BaseConfigHandler):
    """Handler for status display configuration arguments."""

    def handle_args(self, args: Any, manager: Any) -> bool:
        """
        Handle status display arguments for the %llm_config magic.

        Args:
            args: The parsed arguments from the magic command.
            manager: The ChatManager instance.

        Returns:
            bool: True if any status-related action was performed, False otherwise.
        """
        action_taken = False

        if hasattr(args, "status") and args.status:
            action_taken = True
            self._show_status(manager)

        return action_taken

    def _show_status(self, manager):
        """Show current status information."""
        active_persona = manager.get_active_persona()
        overrides = manager.get_overrides()
        history = manager.get_history()

        # Use extract_metadata_for_status to get model from last assistant message
        last_assistant = next((m for m in reversed(history) if m.role == "assistant"), None)
        model_used = None
        if last_assistant and last_assistant.metadata:
            meta = extract_metadata_for_status(last_assistant.metadata)
            model_used = meta.get("model_used") or meta.get("model")

        # Calculate token statistics
        total_tokens_in = 0
        total_tokens_out = 0
        total_tokens = 0
        models_used = {}
        estimated_messages = 0

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
            # If message doesn't have token metadata but has content, estimate tokens
            elif msg.content:
                # Use token utils to estimate token count
                estimated_tokens = count_tokens(msg.content)
                if msg.role == "user" or msg.role == "system":
                    total_tokens_in += estimated_tokens
                elif msg.role == "assistant":
                    total_tokens_out += estimated_tokens
                estimated_messages += 1
                logger.debug(
                    f"Estimated {estimated_tokens} tokens for message without metadata in status display"
                )

        # If no total_tokens were calculated from metadata, use in+out sum
        if total_tokens == 0:
            total_tokens = total_tokens_in + total_tokens_out

        # Get session information
        session_id = getattr(manager, "_session_id", "Unknown")
        adapter_type = os.environ.get("CELLMAGE_ADAPTER", "direct").lower()

        # Check ambient mode status
        try:
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
        if hasattr(manager, "conversation_manager"):
            store = getattr(manager.conversation_manager, "store", None)
            if store:
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
        if model_used:
            print(f"  📝 Last Model Used: {model_used}")
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
            if estimated_messages > 0:
                print(
                    f"      - Includes {estimated_messages} estimated message{'s' if estimated_messages > 1 else ''}"
                )

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
            jira_available = "cellmage.magic_commands.tools.jira_magic" in sys.modules
            print(f"    • Jira: {'✅ Loaded' if jira_available else '❌ Not loaded'}")
        except Exception:
            print("    • Jira: ❓ Unknown")

        # Check for GitLab integration
        try:
            gitlab_available = "cellmage.magic_commands.tools.gitlab_magic" in sys.modules
            print(f"    • GitLab: {'✅ Loaded' if gitlab_available else '❌ Not loaded'}")
        except Exception:
            print("    • GitLab: ❓ Unknown")

        # Check for GitHub integration
        try:
            github_available = "cellmage.magic_commands.tools.github_magic" in sys.modules
            print(f"    • GitHub: {'✅ Loaded' if github_available else '❌ Not loaded'}")
        except Exception:
            print("    • GitHub: ❓ Unknown")

        # Check for Confluence integration
        try:
            confluence_available = "cellmage.magic_commands.tools.confluence_magic" in sys.modules
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
