import logging
import uuid
from datetime import datetime
from typing import ClassVar, Dict, List, Optional

from .interfaces import ContextProvider, HistoryStore
from .models import ConversationMetadata, Message
from .utils.token_utils import count_tokens


class HistoryManager:
    """
    Manages conversation history, including cell ID tracking and rollback for notebook re-execution.

    Features:
    - Tracks message history
    - Associates messages with execution cells
    - Handles automatic rollback when cells are re-executed
    - Saves and loads conversations
    """

    # Class variable to track the singleton instance
    _instance: ClassVar[Optional["HistoryManager"]] = None

    # Class variable to persist history across instances
    _global_history: ClassVar[List[Message]] = []

    def __new__(cls, *args, **kwargs):
        """
        Implement singleton pattern to ensure history is preserved across multiple
        instantiations in the same Python process.
        """
        if cls._instance is None:
            cls._instance = super(HistoryManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        history_store: Optional[HistoryStore] = None,
        context_provider: Optional[ContextProvider] = None,
    ):
        """
        Initialize the history manager.

        Args:
            history_store: Optional store for saving/loading conversations
            context_provider: Optional provider for execution context
        """
        # Only initialize once due to singleton pattern
        if getattr(self, "_initialized", False):
            # Update providers if they've changed
            if history_store is not None:
                self.history_store = history_store
            if context_provider is not None:
                self.context_provider = context_provider
            return

        self.logger = logging.getLogger(__name__)

        # Use the class-level global history to persist across instances
        if not HistoryManager._global_history:
            self.history = []
            HistoryManager._global_history = self.history
        else:
            self.history = HistoryManager._global_history
            self.logger.debug(f"Using existing history with {len(self.history)} messages")

        self.cell_last_history_index: Dict[str, int] = {}
        self.history_store = history_store
        self.context_provider = context_provider
        self.current_save_path: Optional[str] = None
        self._initialized = True
        self.logger.debug("HistoryManager initialized with singleton pattern")

    def add_message(self, message: Message) -> None:
        """
        Add a message to the history.

        If a cell ID is provided and it has been seen before, this may trigger
        a history rollback to handle re-execution of cells in notebooks.

        Args:
            message: The message to add
        """
        # If message doesn't have execution context, try to get it
        if (message.execution_count is None or message.cell_id is None) and self.context_provider:
            exec_count, cell_id = self.context_provider.get_execution_context()
            if message.execution_count is None:
                message.execution_count = exec_count
            if message.cell_id is None:
                message.cell_id = cell_id

        # Add the message to history
        self.history.append(message)

        # Ensure the class-level history is updated
        if HistoryManager._global_history is not self.history:
            HistoryManager._global_history = self.history
            self.logger.debug("Updated global history reference")

        # Update cell tracking if we have a cell ID
        if message.cell_id:
            current_idx = len(self.history) - 1
            self.cell_last_history_index[message.cell_id] = current_idx
            self.logger.debug(
                f"Updated tracking for cell ID {message.cell_id} to history index {current_idx}"
            )

        # Clear current save path since history has changed
        self.current_save_path = None
        self.logger.debug(f"History now has {len(self.history)} messages")

    def perform_rollback(self, cell_id: Optional[str] = None) -> bool:
        """
        Perform a rollback for a particular cell ID if needed.
        This is a wrapper around check_and_rollback for clarity in the API.

        Args:
            cell_id: The cell ID to perform rollback for

        Returns:
            True if rollback was performed, False otherwise
        """
        return self.check_and_rollback(cell_id)

    def check_and_rollback(self, cell_id: Optional[str] = None) -> bool:
        """
        Check if a cell is being re-executed and rollback history if needed.

        Args:
            cell_id: The cell ID to check, or current cell ID if None

        Returns:
            True if history was rolled back, False otherwise
        """
        if not cell_id and self.context_provider:
            _, cell_id = self.context_provider.get_execution_context()

        if not cell_id:
            self.logger.debug("No cell ID available, skipping rollback check")
            return False

        # Check if this cell has been executed before
        if cell_id in self.cell_last_history_index:
            previous_end_index = self.cell_last_history_index[cell_id]

            # Only rollback if the previous message is still in history and was from the assistant
            if (
                0 <= previous_end_index < len(self.history)
                and self.history[previous_end_index].role == "assistant"
            ):
                # We need to remove the user message and assistant response for this cell
                start_index = previous_end_index - 1
                if start_index >= 0 and self.history[start_index].role == "user":
                    self.logger.info(
                        f"Cell rerun detected (ID: {cell_id}). Rolling back history from {start_index}."
                    )

                    # Remove messages from this cell's previous execution
                    self.history = self.history[:start_index]

                    # Remove cell tracking
                    del self.cell_last_history_index[cell_id]

                    # Clear current save path since history has changed
                    self.current_save_path = None

                    return True

        return False

    def get_history(self, include_all=True) -> List[Message]:
        """
        Get a copy of the current history.

        Args:
            include_all: Whether to include all messages (including system messages and
                         integration-generated messages). Should always be True.
                         Parameter is kept for backward compatibility.

        Returns:
            A copy of the complete history list with all messages
        """
        # Always return the complete history without any filtering
        # Debug any possibility of empty history
        if not self.history:
            self.logger.debug("get_history: History list is empty")
        else:
            # Log sources and roles for debugging
            sources = {}
            roles = {}

            for msg in self.history:
                # Count by role
                roles[msg.role] = roles.get(msg.role, 0) + 1

                # Count integration sources
                if msg.metadata and "source" in msg.metadata:
                    source = msg.metadata.get("source")
                    if source:
                        sources[source] = sources.get(source, 0) + 1

            self.logger.debug(f"get_history: Returning {len(self.history)} messages")
            self.logger.debug(f"get_history: Roles breakdown: {roles}")

            if sources:
                self.logger.debug(f"get_history: Integration sources: {sources}")

        # Add extra debug info
        self.logger.debug(f"Memory ID of history list: {id(self.history)}")
        self.logger.debug(f"History state at retrieval: {[m.role for m in self.history]}")

        return self.history.copy()

    def clear_history(self, keep_system: bool = True) -> None:
        """
        Clear the conversation history.

        Args:
            keep_system: Whether to keep system messages
        """
        if keep_system:
            # Keep system messages
            system_messages = [m for m in self.history if m.role == "system"]
            self.history = system_messages
        else:
            # Clear all history
            self.history = []

        # Clear cell tracking
        self.cell_last_history_index = {}

        # Clear current save path since history has changed
        self.current_save_path = None

        self.logger.info(
            f"History cleared. Kept {len(self.history)} system messages."
            if keep_system
            else "All history cleared."
        )

    def save_conversation(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Save the conversation to a file.

        Args:
            filename: Optional filename (without extension) to use

        Returns:
            Path to the saved file or None on failure
        """
        if not self.history_store:
            self.logger.error("Cannot save: No history store configured")
            return None

        if not self.history:
            self.logger.warning("Cannot save: History is empty")
            return None

        # Count tokens from message metadata
        total_tokens = 0

        for message in self.history:
            # If the message has token metadata, use it
            if message.metadata and (
                "tokens_in" in message.metadata or "tokens_out" in message.metadata
            ):
                total_tokens += message.metadata.get("tokens_in", 0)
                total_tokens += message.metadata.get("tokens_out", 0)
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
                elif message.role == "assistant":
                    message.metadata["tokens_out"] = message_tokens

        # Find current persona name and model if available
        persona_name = None
        model_name = None

        # Try to get model and persona from the most recent assistant message
        for message in reversed(self.history):
            if (
                message.role == "assistant"
                and message.metadata
                and "model_used" in message.metadata
            ):
                model_name = message.metadata.get("model_used")
                break

        # Create metadata that matches the ConversationMetadata class definition
        metadata = ConversationMetadata(
            session_id=str(uuid.uuid4()),
            saved_at=datetime.now(),
            persona_name=persona_name,
            model_name=model_name,
            total_tokens=total_tokens if total_tokens > 0 else None,
        )

        try:
            # Save using the history store
            self.current_save_path = self.history_store.save_conversation(
                messages=self.history, metadata=metadata, filename=filename
            )
            return self.current_save_path
        except Exception as e:
            self.logger.error(f"Error saving conversation: {e}")
            return None

    def load_conversation(self, filepath: str) -> bool:
        """
        Load a conversation from a file.

        Args:
            filepath: Path to the conversation file

        Returns:
            True if successfully loaded, False otherwise
        """
        if not self.history_store:
            self.logger.error("Cannot load: No history store configured")
            return False

        try:
            # Load using the history store
            messages, metadata = self.history_store.load_conversation(filepath)

            # Replace current history with loaded messages
            self.history = messages

            # Clear cell tracking since the cell IDs in the loaded conversation
            # might not be relevant to the current session
            self.cell_last_history_index = {}

            # Set current save path
            self.current_save_path = filepath

            self.logger.info(f"Loaded conversation from {filepath} with {len(messages)} messages")
            return True
        except Exception as e:
            self.logger.error(f"Error loading conversation: {e}")
            return False
