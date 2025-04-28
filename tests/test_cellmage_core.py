import os
import sys
import unittest
import uuid
from unittest.mock import MagicMock

# Add the parent directory to path so we can import cellmage
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cellmage
from cellmage.exceptions import (
    NotebookLLMError,
)
from cellmage.models import ConversationMetadata, Message
from cellmage.resources.memory_loader import MemoryLoader
from cellmage.storage.memory_store import MemoryStore


class TestCellmageCore(unittest.TestCase):
    """Test basic functionality of cellmage core components."""

    def setUp(self):
        """Set up test resources."""
        # Create memory-based components for testing
        self.memory_loader = MemoryLoader()
        self.memory_store = MemoryStore()

        # Mock context provider
        self.context_provider = MagicMock()
        self.context_provider.get_execution_context.return_value = (1, "test-cell-id")

        # Mock LLM client
        self.llm_client = MagicMock()
        self.llm_client.chat.return_value = "This is a mock LLM response"

        # Add test persona
        self.memory_loader.add_persona(
            name="test_persona",
            system_message="You are a test assistant",
            config={"temperature": 0.7, "model": "test-model"},
        )

        # Add test snippet
        self.memory_loader.add_snippet(name="test_snippet", content="This is a test snippet")

    def test_memory_loader(self):
        """Test the memory loader for personas and snippets."""
        # Test persona listing and retrieval
        personas = self.memory_loader.list_personas()
        self.assertIn("test_persona", personas)

        persona = self.memory_loader.get_persona("test_persona")
        self.assertIsNotNone(persona)
        self.assertEqual(persona.system_message, "You are a test assistant")
        self.assertEqual(persona.config.get("temperature"), 0.7)

        # Test snippet listing and retrieval
        snippets = self.memory_loader.list_snippets()
        self.assertIn("test_snippet", snippets)

        snippet = self.memory_loader.get_snippet("test_snippet")
        self.assertEqual(snippet, "This is a test snippet")

        # Test case insensitivity
        persona = self.memory_loader.get_persona("TEST_PERSONA")
        self.assertIsNotNone(persona)

        snippet = self.memory_loader.get_snippet("TEST_SNIPPET")
        self.assertIsNotNone(snippet)

        # Test non-existent resources
        self.assertIsNone(self.memory_loader.get_persona("non_existent"))
        self.assertIsNone(self.memory_loader.get_snippet("non_existent"))

    def test_memory_store(self):
        """Test the memory store for conversation storage."""
        # Create test messages and metadata
        messages = [
            Message(role="system", content="System message", id=str(uuid.uuid4())),
            Message(role="user", content="User message", id=str(uuid.uuid4())),
            Message(role="assistant", content="Assistant message", id=str(uuid.uuid4())),
        ]

        metadata = ConversationMetadata(total_messages=len(messages), turns=1)

        # Test saving
        identifier = self.memory_store.save_conversation(messages, metadata, "test_conversation")
        self.assertEqual(identifier, "test_conversation")

        # Test listing
        conversations = self.memory_store.list_saved_conversations()
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0]["identifier"], "test_conversation")

        # Test loading
        loaded_messages, loaded_metadata = self.memory_store.load_conversation("test_conversation")
        self.assertEqual(len(loaded_messages), len(messages))
        self.assertEqual(loaded_messages[0].role, "system")
        self.assertEqual(loaded_messages[1].role, "user")
        self.assertEqual(loaded_messages[2].role, "assistant")

        # Test deleting
        self.assertTrue(self.memory_store.delete_conversation("test_conversation"))
        conversations = self.memory_store.list_saved_conversations()
        self.assertEqual(len(conversations), 0)

        # Test error on loading non-existent conversation
        with self.assertRaises(Exception):
            self.memory_store.load_conversation("non_existent")

    def test_history_manager(self):
        """Test the history manager."""
        from cellmage.history_manager import HistoryManager

        # Create history manager with context provider
        history_manager = HistoryManager(
            history_store=self.memory_store, context_provider=self.context_provider
        )

        # Add test messages
        msg1 = Message(role="system", content="System message", id=str(uuid.uuid4()))
        msg2 = Message(role="user", content="User message", id=str(uuid.uuid4()))
        msg3 = Message(role="assistant", content="Assistant message", id=str(uuid.uuid4()))

        history_manager.add_message(msg1)
        history_manager.add_message(msg2)
        history_manager.add_message(msg3)

        # Test history retrieval
        history = history_manager.get_history()
        self.assertEqual(len(history), 3)

        # Test cell ID tracking
        self.assertIn("test-cell-id", history_manager.cell_last_history_index)

        # Test rollback
        # The current implementation will rollback because the assistant message
        # was just added with the same cell ID - this is expected behavior
        rollback = history_manager.check_and_rollback("test-cell-id")
        # Update test to expect True since rollback should occur with same cell ID
        self.assertTrue(rollback)

        # After rollback, history should only contain the system message
        history = history_manager.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].role, "system")

        # Clear all history
        history_manager.clear_history(keep_system=False)
        self.assertEqual(len(history_manager.get_history()), 0)

    def test_chat_manager(self):
        """Test the chat manager with mocked components."""
        # Create chat manager with mocked components
        chat_manager = cellmage.ChatManager(
            llm_client=self.llm_client,
            persona_loader=self.memory_loader,
            snippet_provider=self.memory_loader,
            history_store=self.memory_store,
            context_provider=self.context_provider,
        )

        # Test persona operations
        personas = chat_manager.list_personas()
        self.assertIn("test_persona", personas)

        chat_manager.set_default_persona("test_persona")

        # Verify the LLM client received the correct overrides
        self.llm_client.set_override.assert_any_call("temperature", 0.7)
        self.llm_client.set_override.assert_any_call("model", "test-model")

        # Test snippet operations
        snippets = chat_manager.list_snippets()
        self.assertIn("test_snippet", snippets)

        chat_manager.add_snippet("test_snippet")

        # Explicitly disable streaming in the test to get direct mock response
        response = chat_manager.chat("Hello world", stream=False)
        self.assertEqual(response, "This is a mock LLM response")

        # Verify LLM client was called with the correct parameters
        self.llm_client.chat.assert_called()
        call_args = self.llm_client.chat.call_args
        self.assertTrue(call_args is not None)

        # Check history after chat
        history = chat_manager.get_history()
        # History contains: system message + snippet + user message + assistant message
        self.assertEqual(len(history), 4)

        # Test override operations
        chat_manager.set_override("max_tokens", 100)
        self.llm_client.set_override.assert_any_call("max_tokens", 100)

        chat_manager.remove_override("max_tokens")
        self.llm_client.remove_override.assert_called_with("max_tokens")

        chat_manager.clear_overrides()
        self.llm_client.clear_overrides.assert_called()

        # Test error handling with failing LLM client
        self.llm_client.chat.side_effect = Exception("LLM failure")

        with self.assertRaises(NotebookLLMError):
            chat_manager.chat("This should fail", stream=False)


if __name__ == "__main__":
    unittest.main()
