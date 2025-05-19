"""
Persistence commands for CellMage.

This module provides commands for saving and loading conversations,
and utilities for working with the SQLite storage system.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..chat_manager import ChatManager
from ..conversation_manager import ConversationManager
from ..models import ConversationMetadata, Message
from ..storage.sqlite_store import SQLiteStore

# Logging setup
logger = logging.getLogger(__name__)


def migrate_to_sqlite(manager: ChatManager, db_path: Optional[str] = None) -> ConversationManager:
    """
    Migrate conversations from current storage to SQLite.

    Args:
        manager: Current ChatManager instance
        db_path: Optional path to SQLite database

    Returns:
        ConversationManager using SQLite storage
    """
    # Create a new ConversationManager with SQLite storage
    conversation_manager = ConversationManager(
        db_path=db_path, context_provider=manager.context_provider
    )

    # Import current history into the conversation manager
    current_history = []
    if hasattr(manager, "conversation_manager") and manager.conversation_manager:
        current_history = manager.conversation_manager.get_messages()
        for msg in current_history:
            conversation_manager.add_message(msg)

    logger.info(f"Migrated {len(current_history)} messages to SQLite storage")

    # Try to migrate saved conversations if they exist
    try:
        # Skip migration of saved conversations as we've removed history_manager support
        pass
    except Exception as e:
        logger.error(f"Error during saved conversation migration: {e}")

    return conversation_manager


def export_conversation_to_markdown(
    conversation_manager: ConversationManager,
    conversation_id: Optional[str] = None,
    filepath: Optional[str] = None,
) -> Optional[str]:
    """
    Export a conversation to a markdown file.

    Args:
        conversation_manager: ConversationManager instance
        conversation_id: ID of conversation to export, or current if None
        filepath: Path to save the markdown file, or auto-generated if None

    Returns:
        Path to the saved file or None on failure
    """
    try:
        # Use current conversation if no ID provided
        conv_id = conversation_id or conversation_manager.current_conversation_id

        # If conversation_id is provided but not current, load it first
        messages = conversation_manager.messages
        if conversation_id and conversation_id != conversation_manager.current_conversation_id:
            # Need to load the specified conversation
            if conversation_id.startswith("sqlite://"):
                conversation_id = conversation_id[len("sqlite://") :]

            # Use SQLiteStore directly to avoid changing current conversation
            store = SQLiteStore()
            loaded_messages, metadata = store.load_conversation(f"sqlite://{conversation_id}")
            messages = loaded_messages

        # Generate output path if not provided
        if not filepath:
            # Create output directory if it doesn't exist
            output_dir = Path.home() / "cellmage_exports"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = output_dir / f"conversation_{timestamp}.md"
        else:
            # Ensure the directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # Format the markdown content
        md_content = []

        # Add header
        md_content.append("# Exported Conversation\n")
        md_content.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md_content.append(f"Conversation ID: {conv_id}\n")

        # Add message count
        md_content.append(f"Message Count: {len(messages)}\n")

        # Calculate tokens
        total_tokens_in = 0
        total_tokens_out = 0
        for msg in messages:
            if msg.metadata:
                total_tokens_in += msg.metadata.get("tokens_in", 0) or 0
                total_tokens_out += msg.metadata.get("tokens_out", 0) or 0

        if total_tokens_in > 0 or total_tokens_out > 0:
            md_content.append(
                f"Total Tokens: {total_tokens_in + total_tokens_out} (Input: {total_tokens_in}, Output: {total_tokens_out})\n"
            )

        # Add messages
        for i, msg in enumerate(messages):
            role_prefix = {
                "system": "💻 System",
                "user": "👤 User",
                "assistant": "🤖 Assistant",
            }.get(msg.role, "❓ Unknown")

            md_content.append(f"## {role_prefix} Message {i + 1}\n")

            # Add message content
            md_content.append("```")
            md_content.append(msg.content)
            md_content.append("```\n")

            # Add metadata if available
            if msg.metadata:
                md_content.append("### Metadata\n")
                md_content.append("```json")
                # Format JSON-like but in a more readable format
                for key, value in msg.metadata.items():
                    md_content.append(f'  "{key}": {repr(value)},')
                md_content.append("```\n")

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))

        return str(filepath)

    except Exception as e:
        logger.error(f"Error exporting conversation to markdown: {e}")
        return None


def import_markdown_to_sqlite(conversation_manager: ConversationManager, filepath: str) -> bool:
    """
    Import a markdown conversation into SQLite.

    Args:
        conversation_manager: ConversationManager instance
        filepath: Path to the markdown file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read markdown file
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse content to extract messages
        # This is a simple implementation - in a real system we'd want a more robust parser
        sections = content.split("##")

        # Create a new conversation
        conversation_manager.create_new_conversation()

        # Process each section (skip the first as it's before any ##)
        for section in sections[1:]:
            if not section.strip():
                continue

            # Extract role from section header
            if "👤 User" in section:
                role = "user"
            elif "🤖 Assistant" in section:
                role = "assistant"
            elif "💻 System" in section:
                role = "system"
            else:
                continue  # Skip unknown roles

            # Extract content between code blocks
            content_blocks = section.split("```")
            if len(content_blocks) < 3:
                continue  # Skip if no proper content block

            message_content = content_blocks[1].strip()

            # Create message and add to conversation
            message = Message(role=role, content=message_content, id=str(uuid.uuid4()))

            # Try to extract metadata
            if "### Metadata" in section:
                try:
                    metadata_blocks = section.split("### Metadata")
                    if len(metadata_blocks) > 1:
                        metadata_text = metadata_blocks[1].split("```")[1].strip()

                        # Convert text to dictionary (simplified approach)
                        metadata = {}
                        for line in metadata_text.split("\n"):
                            line = line.strip()
                            if not line or line.startswith("```") or ":" not in line:
                                continue

                            key, value_str = line.split(":", 1)
                            key = key.strip().strip("\"'")
                            value_str = value_str.strip().strip(",")

                            # Try to parse value
                            try:
                                # Simple types
                                if value_str.lower() == "true":
                                    value = True
                                elif value_str.lower() == "false":
                                    value = False
                                elif value_str.lower() == "none":
                                    value = None
                                else:
                                    # Try as number
                                    try:
                                        if "." in value_str:
                                            value = float(value_str)
                                        else:
                                            value = int(value_str)
                                    except Exception:
                                        # Keep as string
                                        value = value_str.strip().strip("'\"")

                                metadata[key] = value
                            except Exception:
                                pass  # Skip if parsing fails

                        message.metadata = metadata
                except Exception as e:
                    logger.warning(f"Error parsing metadata: {e}")

            # Add message to conversation
            conversation_manager.add_message(message)

        return True

    except Exception as e:
        logger.error(f"Error importing markdown to SQLite: {e}")
        return False


def list_sqlite_conversations(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all conversations in SQLite storage.

    Args:
        db_path: Path to SQLite database file

    Returns:
        List of conversation metadata dictionaries
    """
    try:
        store = SQLiteStore(db_path)
        return store.list_saved_conversations()
    except Exception as e:
        logger.error(f"Error listing SQLite conversations: {e}")
        return []


def get_sqlite_conversation(
    conversation_id: str, db_path: Optional[str] = None
) -> Tuple[List[Message], ConversationMetadata]:
    """
    Get a specific conversation from SQLite storage.

    Args:
        conversation_id: ID of conversation to retrieve
        db_path: Path to SQLite database file

    Returns:
        Tuple of (messages, metadata)
    """
    try:
        store = SQLiteStore(db_path)

        # Add sqlite:// prefix if not present
        if not conversation_id.startswith("sqlite://"):
            conversation_id = f"sqlite://{conversation_id}"

        return store.load_conversation(conversation_id)
    except Exception as e:
        logger.error(f"Error getting SQLite conversation {conversation_id}: {e}")
        return [], ConversationMetadata()


def delete_sqlite_conversation(conversation_id: str, db_path: Optional[str] = None) -> bool:
    """
    Delete a conversation from SQLite storage.

    Args:
        conversation_id: ID of conversation to delete
        db_path: Path to SQLite database file

    Returns:
        True if successful, False otherwise
    """
    try:
        store = SQLiteStore(db_path)
        return store.delete_conversation(conversation_id)
    except Exception as e:
        logger.error(f"Error deleting SQLite conversation {conversation_id}: {e}")
        return False


def tag_sqlite_conversation(conversation_id: str, tag: str, db_path: Optional[str] = None) -> bool:
    """
    Add a tag to a conversation in SQLite storage.

    Args:
        conversation_id: ID of conversation to tag
        tag: Tag to add
        db_path: Path to SQLite database file

    Returns:
        True if successful, False otherwise
    """
    try:
        store = SQLiteStore(db_path)
        return store.add_tag(conversation_id, tag)
    except Exception as e:
        logger.error(f"Error tagging SQLite conversation {conversation_id}: {e}")
        return False


def search_sqlite_conversations(
    query: str, limit: int = 20, db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for conversations in SQLite storage.

    Args:
        query: Search query string
        limit: Maximum number of results to return
        db_path: Path to SQLite database file

    Returns:
        List of matching conversation metadata
    """
    try:
        store = SQLiteStore(db_path)
        return store.search_conversations(query, limit)
    except Exception as e:
        logger.error(f"Error searching SQLite conversations: {e}")
        return []


def get_sqlite_statistics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Get statistics about conversations in SQLite storage.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Dictionary with statistics
    """
    try:
        store = SQLiteStore(db_path)
        return store.get_statistics()
    except Exception as e:
        logger.error(f"Error getting SQLite statistics: {e}")
        return {"error": str(e)}
