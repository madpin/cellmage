"""
Base directory configuration handler for the %llm_config magic command.

This module handles base directory arguments for the %llm_config magic command.
"""

import logging
from pathlib import Path
from typing import Any

from .base_config_handler import BaseConfigHandler

logger = logging.getLogger(__name__)


class BaseDirConfigHandler(BaseConfigHandler):
    """Handler for base directory configuration arguments."""

    def handle_args(self, args: Any, manager: Any) -> bool:
        action_taken = False
        if hasattr(args, "base_dir") and args.base_dir:
            action_taken = True
            import os

            from cellmage.config import settings

            # Accept both absolute and relative paths, relative to current working directory
            new_base_dir = os.path.abspath(os.path.expanduser(args.base_dir))
            os.environ["CELLMAGE_BASE_DIR"] = new_base_dir
            # Force update of all config fields to use the new base dir
            settings.personas_dir = str(Path(new_base_dir) / "llm_personas")
            settings.snippets_dir = str(Path(new_base_dir) / "llm_snippets")
            settings.conversations_dir = str(Path(new_base_dir) / "llm_conversations")
            settings.log_file = str(Path(new_base_dir) / "cellmage.log")
            settings.gdocs_token_path = str(
                Path(new_base_dir) / "gdocs_token.pickle:~/.cellmage/gdocs_token.pickle"
            )
            settings.gdocs_credentials_path = str(
                Path(new_base_dir) / "gdocs_credentials.json:~/.cellmage/gdocs_credentials.json"
            )
            settings.gdocs_service_account_path = str(
                Path(new_base_dir)
                / "gdocs_service_account.json:~/.cellmage/gdocs_service_account.json"
            )
            # Also update SQLite path if not overridden by CELLMAGE_SQLITE_PATH
            if not os.environ.get("CELLMAGE_SQLITE_PATH"):
                settings.sqlite_path = str(Path(new_base_dir) / ".data" / "conversations.db")
            print(f"✅ Base directory changed to: {new_base_dir}")
            print("All working directories and files will now use this base directory.")
            # Also update the ChatManager's persona_loader and snippet_provider
            try:
                from IPython import get_ipython

                from cellmage.resources.file_loader import FileLoader

                ipy = get_ipython()
                if ipy and "_cellmage_chat_manager" in ipy.user_ns:
                    chat_manager = ipy.user_ns["_cellmage_chat_manager"]
                    new_loader = FileLoader(settings.personas_dir, settings.snippets_dir)
                    chat_manager.persona_loader = new_loader
                    chat_manager.snippet_provider = new_loader
                    print("🔄 ChatManager resource loaders updated to new base directory.")
            except Exception as e:
                print(f"⚠️ Warning: Could not update ChatManager resource loaders: {e}")
        return action_taken
