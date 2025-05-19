"""
Base class for IPython magic extensions in CellMage.

This module provides a base class with common functionality for all magic command integrations.
"""

import logging
import uuid
from typing import List, Optional, Tuple

try:
    from IPython.core.magic import Magics, magics_class

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

    class DummyMagics:
        """Dummy class when IPython is not available."""

        pass

    Magics = DummyMagics  # Type alias for compatibility

    # Define dummy decorator if IPython is not available
    def magics_class(cls):
        return cls


# Create a logger
logger = logging.getLogger(__name__)


@magics_class
class BaseMagics(Magics):
    """Base class for all IPython magic commands in CellMage."""

    def __init__(self, shell=None):
        """Initialize the base magic utility."""
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not available. Magic commands are disabled.")
            return

        # If shell is None, try to get the current IPython instance
        if shell is None:
            try:
                from IPython import get_ipython

                shell = get_ipython()
            except (ImportError, AttributeError):
                logger.warning("Could not get IPython shell. Magic commands may be limited.")

        super().__init__(shell)

    def llm_magic(self, *args, **kwargs):
        """
        Decorator to register a function as an LLM magic command.

        Args:
            func: The function to register
        """
        return lambda func: func

    def _get_chat_manager(self):
        """Get the ChatManager instance."""
        try:
            # Import from the refactored magic_commands module
            from cellmage.magic_commands.ipython.common import get_chat_manager

            return get_chat_manager()
        except Exception as e:
            logger.error(f"Error getting ChatManager: {e}")
            print(f"❌ Error getting ChatManager: {e}")
            return None

    def _get_execution_context(self) -> Tuple[Optional[int], Optional[str]]:
        """Get the current execution context (exec_count and cell_id)."""
        context_provider = None
        try:
            from cellmage.context_providers.ipython_context_provider import (
                get_ipython_context_provider,
            )

            context_provider = get_ipython_context_provider()
        except Exception as e:
            logger.error(f"Could not get context provider: {e}")

        exec_count, cell_id = (None, None)
        if context_provider:
            exec_count, cell_id = context_provider.get_execution_context()

        return exec_count, cell_id

    def _add_to_history(
        self,
        content: str,
        source_type: str,
        source_id: str,
        source_name: str,
        id_key: str,
        as_system_msg: bool = False,
    ) -> bool:
        """
        Add the content to the chat history as a user or system message.

        Args:
            content: Content to add to the history
            source_type: Type of source (e.g., 'repository', 'pull_request', 'page', 'search')
            source_id: Identifier for the source
            source_name: Name of the source system (e.g., 'github', 'gitlab', 'confluence')
            id_key: Key to use for the source ID in metadata (e.g., 'github_id', 'confluence_id')
            as_system_msg: Whether to add as a system message (default: False)

        Returns:
            True if successful, False otherwise
        """
        from cellmage.models import Message

        manager = self._get_chat_manager()
        if not manager:
            print("❌ Conversation manager not available")
            return False

        try:
            # Get execution context to identify current cell
            exec_count, cell_id = self._get_execution_context()

            # Find and remove any previous content from the same source
            if hasattr(manager, "conversation_manager"):
                # Get current history
                current_history = manager.conversation_manager.get_messages()

                # Look for messages to remove based on their metadata
                indices_to_remove = self._find_messages_to_remove(
                    current_history, source_name, source_type, source_id, id_key
                )

                # If we found messages to remove
                if indices_to_remove:
                    # Create a new history without those messages
                    new_history = [
                        msg for i, msg in enumerate(current_history) if i not in indices_to_remove
                    ]

                    # Clear history and re-add the filtered messages
                    manager.conversation_manager.clear_messages(keep_system=False)
                    for msg in new_history:
                        manager.conversation_manager.add_message(msg)

                    logger.info(
                        f"Removed {len(indices_to_remove)} previous {source_name} {source_type} messages"
                    )

            # Create message with execution context
            role = "system" if as_system_msg else "user"
            metadata = {"source": source_name, id_key: source_id, "type": source_type}
            message = Message(
                role=role,
                content=content,
                id=str(uuid.uuid4()),
                cell_id=cell_id,
                execution_count=exec_count,
                metadata=metadata,
            )

            # Add to history
            manager.conversation_manager.add_message(message)
            print(
                f"✅ Added {source_name} {source_type} {source_id} as {role} message to chat history"
            )
            return True

        except Exception as e:
            logger.error(f"Error adding {source_name} content to history: {e}")
            print(f"❌ Error adding {source_name} content to history: {e}")
            return False

    def _find_messages_to_remove(
        self, history: List, source_name: str, source_type: str, source_id: str, id_key: str
    ) -> List[int]:
        """
        Find messages to remove from history based on source metadata.

        This is a base implementation that should be overridden by subclasses
        for more specific removal strategies.

        Args:
            history: The current message history
            source_name: Name of the source system
            source_type: Type of the content
            source_id: ID of the content
            id_key: Key used for the source ID in metadata

        Returns:
            List of indices to remove
        """
        indices_to_remove = []

        # Basic implementation: remove exact matches
        for i, msg in enumerate(history):
            if (
                msg.metadata
                and msg.metadata.get("source") == source_name
                and msg.metadata.get("type") == source_type
                and msg.metadata.get(id_key) == source_id
            ):
                indices_to_remove.append(i)

        return indices_to_remove
