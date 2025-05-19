"""
Conversation management module.

This module provides a ConversationManager class for managing conversations with different storage backends,
with SQLite as the default and recommended storage option.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import settings
from .interfaces import ContextProvider
from .models import ConversationMetadata, Message
from .storage.memory_store import MemoryStore
from .storage.sqlite_store import SQLiteStore
from .utils.token_utils import count_tokens


class ConversationManager:
    """
    Manages conversation data using configurable storage backends, with SQLite as default.

    This class provides methods for:
    - Creating, retrieving, updating, and deleting conversations
    - Managing messages within conversations
    - Searching and filtering conversations
    - Retrieving conversation statistics and debugging information
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        context_provider: Optional[ContextProvider] = None,
        storage_type: str = "sqlite",
    ):
        """
        Initialize the conversation manager.

        Args:
            db_path: Path to storage (e.g., SQLite database file). If None, uses default location.
            context_provider: Optional context provider for execution context
            storage_type: Storage type to use ('sqlite', 'memory', or 'file'). Defaults to 'sqlite'.
        """
        self.logger = logging.getLogger(__name__)

        # Initialize the appropriate storage backend
        self.storage_type = storage_type.lower()
        self._init_storage(db_path)

        # Set up manager state
        self.context_provider = context_provider
        self.current_conversation_id = str(uuid.uuid4())
        self.messages: List[Message] = []
        self.cell_last_message_index: Dict[str, int] = {}

    def _init_storage(self, db_path: Optional[str] = None) -> None:
        """Initialize the storage backend based on storage_type."""
        if self.storage_type == "sqlite":
            # Use config.settings.sqlite_path_resolved unless db_path is explicitly provided
            resolved_db_path = db_path if db_path is not None else settings.sqlite_path_resolved
            self.store = SQLiteStore(resolved_db_path)
            self.logger.info(f"Using SQLite storage (default) at {resolved_db_path}")
        elif self.storage_type == "memory":
            self.store = MemoryStore()
            self.logger.info("Using in-memory storage (no persistence)")
        else:
            # Fallback to SQLite for unsupported storage types
            self.logger.warning(
                f"Storage type '{self.storage_type}' not supported. Using SQLite instead."
            )
            resolved_db_path = db_path if db_path is not None else settings.sqlite_path_resolved
            self.store = SQLiteStore(resolved_db_path)
            self.storage_type = "sqlite"

    def add_message(self, message: Message) -> str:
        """
        Add a message to the current conversation.

        Args:
            message: Message to add

        Returns:
            ID of the message
        """
        # If message doesn't have execution context, try to get it
        if (message.execution_count is None or message.cell_id is None) and self.context_provider:
            exec_count, cell_id = self.context_provider.get_execution_context()
            if message.execution_count is None:
                message.execution_count = exec_count
            if message.cell_id is None:
                message.cell_id = cell_id

        # Ensure message has an ID that's based on its content and context
        if not message.id:
            message.id = Message.generate_message_id(
                role=message.role,
                content=message.content,
                cell_id=message.cell_id,
                execution_count=message.execution_count,
            )

        # Add the message to our in-memory list
        self.messages.append(message)

        # Update cell tracking if we have a cell ID
        if message.cell_id:
            current_idx = len(self.messages) - 1
            self.cell_last_message_index[message.cell_id] = current_idx
            self.logger.debug(
                f"Updated tracking for cell ID {message.cell_id} to message index {current_idx}"
            )

        # Save to database
        self._save_current_conversation()

        # Log debug information
        if self.store:
            self.store.log_debug(
                self.current_conversation_id,
                "ConversationManager",
                "message_added",
                {
                    "message_id": message.id,
                    "role": message.role,
                    "content_length": len(message.content) if message.content else 0,
                    "has_cell_id": message.cell_id is not None,
                    "execution_count": message.execution_count,
                },
            )

        return message.id

    def get_messages(self) -> List[Message]:
        """
        Get a copy of the current messages.

        Returns:
            A copy of the messages list
        """
        return self.messages.copy()

    def perform_rollback(self, cell_id: Optional[str] = None) -> bool:
        """
        Perform a rollback for a particular cell ID if needed.

        Args:
            cell_id: Cell ID to rollback, or current cell if None

        Returns:
            True if rollback was performed, False otherwise
        """
        if not cell_id and self.context_provider:
            _, cell_id = self.context_provider.get_execution_context()

        if not cell_id:
            self.logger.debug("No cell ID available, skipping rollback check")
            return False

        # Check if this cell has been executed before
        if cell_id in self.cell_last_message_index:
            previous_end_index = self.cell_last_message_index[cell_id]

            # Only rollback if the previous message is still in history and was from the assistant
            if (
                0 <= previous_end_index < len(self.messages)
                and self.messages[previous_end_index].role == "assistant"
            ):
                # We need to remove the user message and assistant response for this cell
                start_index = previous_end_index - 1
                if start_index >= 0 and self.messages[start_index].role == "user":
                    self.logger.info(
                        f"Cell rerun detected (ID: {cell_id}). Rolling back history from {start_index}."
                    )

                    # Remove messages from this cell's previous execution
                    self.messages = self.messages[:start_index]

                    # Remove cell tracking
                    del self.cell_last_message_index[cell_id]

                    # Save changes to database
                    self._save_current_conversation()

                    # Log debug information
                    if self.store:
                        self.store.log_debug(
                            self.current_conversation_id,
                            "ConversationManager",
                            "rollback_performed",
                            {
                                "cell_id": cell_id,
                                "start_index": start_index,
                                "previous_end_index": previous_end_index,
                                "new_message_count": len(self.messages),
                            },
                        )

                    return True

        return False

    def clear_messages(self, keep_system: bool = True) -> None:
        """
        Clear the current conversation messages.

        Args:
            keep_system: Whether to keep system messages
        """
        if keep_system:
            # Keep system messages
            system_messages = [m for m in self.messages if m.role == "system"]
            self.messages = system_messages
        else:
            # Clear all messages
            self.messages = []

        # Clear cell tracking
        self.cell_last_message_index = {}

        # Save empty/system-only conversation
        self._save_current_conversation()

        self.logger.info(
            f"Messages cleared. Kept {len(self.messages)} system messages."
            if keep_system
            else "All messages cleared."
        )

    def create_new_conversation(self) -> str:
        """
        Create a new conversation and make it active.

        Returns:
            ID of the new conversation
        """
        # Save current conversation if it has messages
        if self.messages:
            self._save_current_conversation()

        # Create new conversation
        self.current_conversation_id = str(uuid.uuid4())
        self.messages = []
        self.cell_last_message_index = {}

        self.logger.info(f"Created new conversation with ID: {self.current_conversation_id}")
        return self.current_conversation_id

    def load_conversation(self, conversation_id: str) -> bool:
        """
        Load a conversation by ID and make it the active conversation.

        Args:
            conversation_id: ID of the conversation to load

        Returns:
            True if successful, False otherwise
        """
        try:
            # If the conversation_id doesn't start with sqlite://, add it
            if not conversation_id.startswith("sqlite://"):
                conversation_id = f"sqlite://{conversation_id}"

            # Load the conversation from SQLite
            messages, metadata = self.store.load_conversation(conversation_id)

            # Extract conversation ID from the URI
            if conversation_id.startswith("sqlite://"):
                self.current_conversation_id = conversation_id[len("sqlite://") :]
            else:
                self.current_conversation_id = conversation_id

            # Set as current conversation
            self.messages = messages

            # Clear cell tracking as the cell IDs from the loaded conversation
            # might not be relevant to the current session
            self.cell_last_message_index = {}

            self.logger.info(f"Loaded conversation {conversation_id} with {len(messages)} messages")
            return True

        except Exception as e:
            self.logger.error(f"Error loading conversation: {e}")
            return False

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation by ID.

        Args:
            conversation_id: ID of the conversation to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # If conversation is the current one, create a new conversation after deletion
            is_current = (
                self.current_conversation_id == conversation_id
                or f"sqlite://{self.current_conversation_id}" == conversation_id
            )

            # Delete from storage
            result = self.store.delete_conversation(conversation_id)

            # If this was the current conversation, create a new one
            if is_current and result:
                self.create_new_conversation()

            return result

        except Exception as e:
            self.logger.error(f"Error deleting conversation: {e}")
            return False

    def list_conversations(self) -> List[Dict[str, Any]]:
        """
        List all saved conversations.

        Returns:
            List of conversation metadata dictionaries
        """
        try:
            return self.store.list_saved_conversations()
        except Exception as e:
            self.logger.error(f"Error listing conversations: {e}")
            return []

    def search_conversations(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for conversations by content.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of matching conversation metadata
        """
        try:
            return self.store.search_conversations(query, limit)
        except Exception as e:
            self.logger.error(f"Error searching conversations: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored conversations.

        Returns:
            Dictionary with statistics
        """
        try:
            return self.store.get_statistics()
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}

    def add_tag(self, tag: str) -> bool:
        """
        Add a tag to the current conversation.

        Args:
            tag: Tag to add

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.store.add_tag(self.current_conversation_id, tag)
        except Exception as e:
            self.logger.error(f"Error adding tag: {e}")
            return False

    def remove_tag(self, tag: str) -> bool:
        """
        Remove a tag from the current conversation.

        Args:
            tag: Tag to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.store.remove_tag(self.current_conversation_id, tag)
        except Exception as e:
            self.logger.error(f"Error removing tag: {e}")
            return False

    def _calculate_token_usage(self) -> Dict[str, int]:
        """
        Calculate token usage for the current conversation.

        Returns:
            Dictionary with token counts
        """
        total_tokens = 0
        tokens_in = 0
        tokens_out = 0

        for message in self.messages:
            # If the message has token metadata, use it
            if message.metadata:
                message_tokens_in = message.metadata.get("tokens_in", 0)
                message_tokens_out = message.metadata.get("tokens_out", 0)
                tokens_in += message_tokens_in
                tokens_out += message_tokens_out
                total_tokens += message_tokens_in + message_tokens_out
            # Otherwise, estimate tokens for messages that don't have token counts
            elif message.content:
                # Use token_utils to count tokens in content
                message_tokens = count_tokens(message.content)
                # Add to total
                total_tokens += message_tokens
                # Store in metadata for future reference
                if not message.metadata:
                    message.metadata = {}
                if message.role == "user":
                    message.metadata["tokens_in"] = message_tokens
                    tokens_in += message_tokens
                elif message.role == "assistant":
                    message.metadata["tokens_out"] = message_tokens
                    tokens_out += message_tokens
                else:
                    # For system messages, count as input tokens
                    message.metadata["tokens_in"] = message_tokens
                    tokens_in += message_tokens

        return {"total_tokens": total_tokens, "tokens_in": tokens_in, "tokens_out": tokens_out}

    def _build_conversation_metadata(self) -> ConversationMetadata:
        """
        Build metadata for the current conversation.

        Returns:
            ConversationMetadata object
        """
        # Find current persona name and model if available
        persona_name = None
        model_name = None

        # Try to get model and persona from the most recent assistant message
        for message in reversed(self.messages):
            if message.role == "assistant" and message.metadata:
                if "model_used" in message.metadata:
                    model_name = message.metadata.get("model_used")

                # If we found a model, break
                if model_name:
                    break

        # Get token counts
        token_usage = self._calculate_token_usage()

        # Create metadata
        metadata = ConversationMetadata(
            session_id=self.current_conversation_id,
            saved_at=datetime.now(),
            persona_name=persona_name,
            model_name=model_name,
            total_tokens=token_usage["total_tokens"] if token_usage["total_tokens"] > 0 else None,
        )

        return metadata

    def _save_current_conversation(self) -> Optional[str]:
        """
        Save the current conversation to SQLite.

        Returns:
            URI of the saved conversation or None on failure
        """
        if not self.store:
            self.logger.error("Cannot save: No store configured")
            return None

        if not self.messages:
            self.logger.warning("Cannot save: No messages to save")
            return None

        try:
            # Build metadata
            metadata = self._build_conversation_metadata()

            # Save using the store
            self.logger.debug(f"Saving conversation with ID: {self.current_conversation_id}")
            save_path = self.store.save_conversation(
                messages=self.messages, metadata=metadata, filename=self.current_conversation_id
            )

            return save_path

        except Exception as e:
            self.logger.error(f"Error saving conversation: {e}")
            return None
