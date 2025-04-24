from typing import List, Dict, Any, Tuple
import logging
from datetime import datetime

from ..interfaces import HistoryStore
from ..models import Message, ConversationMetadata
from ..exceptions import PersistenceError, ResourceNotFoundError

logger = logging.getLogger(__name__)

class MemoryStore(HistoryStore):
    """In-memory implementation for storing/retrieving conversation history, useful for testing."""

    _store: Dict[str, Tuple[List[Message], ConversationMetadata]]

    def __init__(self):
        """Initializes the in-memory store."""
        self._store = {}
        logger.info("MemoryStore initialized.")

    def save(self, messages: List[Message], metadata: ConversationMetadata) -> str:
        """Saves the history and metadata to the internal dictionary."""
        identifier = metadata.session_id
        logger.debug(f"Attempting to save session '{identifier}' to memory.")
        # Store copies to avoid external modification issues
        self._store[identifier] = (
            [msg.model_copy(deep=True) for msg in messages],
            metadata.model_copy(deep=True)
        )
        logger.info(f"Successfully saved session '{identifier}' to memory.")
        return identifier # Return the identifier used

    def load(self, identifier: str) -> Tuple[List[Message], ConversationMetadata]:
        """Loads history and metadata from the internal dictionary."""
        logger.debug(f"Attempting to load session '{identifier}' from memory.")
        if identifier not in self._store:
            raise ResourceNotFoundError("history", identifier)

        # Return copies to prevent modification of the stored data
        messages, metadata = self._store[identifier]
        logger.info(f"Successfully loaded session '{identifier}' from memory.")
        return [msg.model_copy(deep=True) for msg in messages], metadata.model_copy(deep=True)

    def list_saved(self) -> List[str]:
        """Lists identifiers (keys) of saved histories in the store."""
        return sorted(list(self._store.keys()))

    # --- Helper methods for testing ---
    def clear_store(self):
        """Clears all data from the memory store."""
        self._store = {}
        logger.info("Memory store cleared.")

    def get_store_content(self) -> Dict[str, Tuple[List[Message], ConversationMetadata]]:
         """Returns the raw content of the store (primarily for debugging/testing)."""
         return self._store
