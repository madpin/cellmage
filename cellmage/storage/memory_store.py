import copy
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..exceptions import PersistenceError
from ..interfaces import HistoryStore
from ..models import ConversationMetadata, Message


class MemoryStore(HistoryStore):
    """
    In-memory implementation of the HistoryStore interface.

    This class stores conversations in memory, allowing for fast access
    but without persistence across program restarts.
    """

    def __init__(self):
        """Initialize the memory store."""
        self.logger = logging.getLogger(__name__)
        self.conversations: Dict[str, Tuple[List[Message], ConversationMetadata]] = {}
        self.logger.debug("MemoryStore initialized")

    def save_conversation(
        self,
        messages: List[Message],
        metadata: ConversationMetadata,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """
        Save a conversation to memory.

        Args:
            messages: List of messages in the conversation
            metadata: Metadata about the conversation
            filename: Optional identifier for the conversation

        Returns:
            Identifier for the saved conversation
        """
        if not messages:
            self.logger.warning("Cannot save empty conversation")
            return None

        # Use provided filename or generate a unique ID
        identifier = filename or str(uuid.uuid4())

        # Create deep copies to avoid external modification
        message_copies = copy.deepcopy(messages)
        metadata_copy = copy.deepcopy(metadata)

        # Update saved timestamp
        metadata_copy.saved_at = datetime.now()

        # Store the conversation
        self.conversations[identifier] = (message_copies, metadata_copy)

        self.logger.info(f"Saved conversation to memory with ID: {identifier}")
        return identifier

    def load_conversation(self, filepath: str) -> Tuple[List[Message], ConversationMetadata]:
        """
        Load a conversation from memory.

        Args:
            filepath: Identifier for the conversation

        Returns:
            Tuple of (messages, metadata)

        Raises:
            PersistenceError: If the conversation is not found
        """
        if filepath not in self.conversations:
            self.logger.error(f"Conversation '{filepath}' not found")
            raise PersistenceError(f"Conversation '{filepath}' not found")

        # Return deep copies to avoid external modification
        messages, metadata = self.conversations[filepath]
        return copy.deepcopy(messages), copy.deepcopy(metadata)

    def list_saved_conversations(self) -> List[Dict[str, Any]]:
        """
        List available saved conversations.

        Returns:
            List of conversation metadata dicts with identifiers
        """
        result = []
        for identifier, (_, metadata) in self.conversations.items():
            # Create a dict representation of the metadata
            meta_dict = {
                "identifier": identifier,
                "saved_at": metadata.saved_at.isoformat(),
                "total_messages": metadata.total_messages,
                "turns": metadata.turns,
                "default_model_name": metadata.default_model_name,
                "default_personality_name": metadata.default_personality_name,
            }
            result.append(meta_dict)

        return result

    def delete_conversation(self, identifier: str) -> bool:
        """
        Delete a conversation from memory.

        Args:
            identifier: Identifier for the conversation

        Returns:
            True if deleted, False if not found
        """
        if identifier in self.conversations:
            del self.conversations[identifier]
            self.logger.info(f"Deleted conversation: {identifier}")
            return True
        else:
            self.logger.warning(f"Cannot delete: Conversation '{identifier}' not found")
            return False

    def clear_all(self) -> int:
        """
        Clear all conversations from memory.

        Returns:
            Number of conversations deleted
        """
        count = len(self.conversations)
        self.conversations.clear()
        self.logger.info(f"Cleared all {count} conversations from memory")
        return count
