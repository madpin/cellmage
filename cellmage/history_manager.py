from typing import List, Optional, Tuple, Dict
from .models import Message
from .exceptions import HistoryManagementError
import logging

logger = logging.getLogger(__name__)

class HistoryManager:
    """Manages the in-memory list of messages for a session, including rollback logic."""
    _messages: List[Message]
    _cell_tracking: Dict[str, int] # Maps cell_id -> index of *last* message added by that cell

    def __init__(self, initial_messages: Optional[List[Message]] = None):
        """Initializes the history manager."""
        self._messages = initial_messages or []
        self._cell_tracking = {}
        self._rebuild_tracking()
        logger.debug(f"HistoryManager initialized with {len(self._messages)} messages.")

    def add_message(self, message: Message):
        """Adds a single message and updates cell tracking if applicable."""
        if not isinstance(message, Message):
            raise TypeError("Can only add Message objects to history.")
        self._messages.append(message)
        if message.cell_id:
            self._cell_tracking[message.cell_id] = len(self._messages) - 1
        logger.debug(f"Added message (Role: {message.role}, Cell: {message.cell_id})")

    def add_messages(self, messages: List[Message]):
        """Adds multiple messages sequentially."""
        for msg in messages:
            self.add_message(msg) # Ensures tracking is updated per message

    def get_history(self) -> List[Message]:
        """Returns a shallow copy of the current message history."""
        return self._messages[:]

    def set_history(self, messages: List[Message]):
        """
        Replaces the entire history and rebuilds tracking.
        Use with caution, as it bypasses normal addition logic.
        """
        if not all(isinstance(m, Message) for m in messages):
             raise TypeError("Can only set history with a list of Message objects.")
        self._messages = messages
        self._rebuild_tracking()
        logger.info(f"History explicitly set with {len(self._messages)} messages.")

    def clear(self):
        """Clears all messages and tracking information."""
        self._messages = []
        self._cell_tracking = {}
        logger.info("History cleared.")

    def revert_last_turn(self):
        """
        Removes the last user/assistant pair (or single message if history ends unexpectedly).
        Primarily intended for error recovery during LLM calls.
        """
        if not self._messages:
            logger.debug("Attempted to revert last turn, but history is empty.")
            return

        # Simple revert strategy: remove last 2 if user/assistant pair, else last 1
        count_to_remove = 0
        if len(self._messages) >= 2:
            if self._messages[-2].role == 'user' and self._messages[-1].role == 'assistant':
                count_to_remove = 2
            else:
                count_to_remove = 1 # Unexpected end, remove just the last one
        elif len(self._messages) == 1:
             count_to_remove = 1

        if count_to_remove > 0:
            self._messages = self._messages[:-count_to_remove]
            self._rebuild_tracking() # Easiest way to keep tracking consistent
            logger.info(f"Reverted last {count_to_remove} message(s).")
        else:
            logger.debug("Did not revert messages (no clear user/assistant pair at end).")

    def rollback_to_cell(self, cell_id: str) -> bool:
        """
        Removes history entries associated with the specified cell_id and any subsequent entries.
        This handles the case where a cell is re-executed in a notebook.

        Returns:
            bool: True if a rollback occurred (messages were removed), False otherwise.
        """
        if not cell_id:
            logger.debug("Rollback requested with no cell_id, ignoring.")
            return False

        if cell_id not in self._cell_tracking:
            logger.debug(f"Rollback requested for cell_id '{cell_id[-8:]}', but not found in tracking.")
            return False # Cell ID never added messages or was already rolled back

        last_index_for_cell = self._cell_tracking[cell_id]
        logger.debug(f"Found cell_id '{cell_id[-8:]}' last contributing at index {last_index_for_cell}.")

        # We need to find the index of the *first* message added by this specific cell run.
        # This is tricky because a cell might add multiple messages (user prompt, snippet, assistant response).
        # We iterate backwards from the *last* known index for this cell.
        first_index_for_cell = -1
        for i in range(last_index_for_cell, -1, -1):
            if self._messages[i].cell_id == cell_id:
                first_index_for_cell = i
            elif self._messages[i].cell_id != cell_id:
                # We've gone past the messages for this cell run.
                break
        else:
            # If the loop finishes without break, it means all messages from the start
            # were from this cell (or first_index_for_cell is still -1 if something weird happened).
            if first_index_for_cell == -1: # Should not happen if cell_id is in tracking
                 logger.warning(f"Inconsistent state during rollback for cell_id '{cell_id[-8:]}'.")
                 return False

        rollback_point = first_index_for_cell
        if rollback_point < len(self._messages):
            num_removed = len(self._messages) - rollback_point
            self._messages = self._messages[:rollback_point]
            self._rebuild_tracking() # Rebuild tracking after modification
            logger.info(f"Rolled back {num_removed} message(s) due to cell_id '{cell_id[-8:]}'. New history length: {len(self._messages)}.")
            return True
        else:
            # This case means the cell was the very last thing, and no messages followed.
            # Technically no rollback needed, but log for clarity.
            logger.debug(f"Cell_id '{cell_id[-8:]}' was the last contributor, no subsequent messages to roll back.")
            return False

    def _rebuild_tracking(self):
        """Internal helper to rebuild the cell_id -> last_index mapping."""
        self._cell_tracking = {}
        for i, msg in enumerate(self._messages):
            if msg.cell_id:
                # Store the latest index found for each cell_id
                self._cell_tracking[msg.cell_id] = i
        logger.debug(f"Cell tracking rebuilt. Tracking {len(self._cell_tracking)} unique cell IDs.")

