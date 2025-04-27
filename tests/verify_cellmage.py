#!/usr/bin/env python
"""
A simple verification script for the cellmage library.
This script creates and tests the main components without using unittest.
"""

import os
import sys
import uuid
from unittest.mock import MagicMock

# Disable dotenv loading
os.environ["CELLMAGE_SKIP_DOTENV"] = "1"

# Add the parent directory to path so we can import cellmage
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cellmage.chat_manager import ChatManager
from cellmage.config import Settings
from cellmage.history_manager import HistoryManager
from cellmage.models import ConversationMetadata, Message, PersonaConfig
from cellmage.resources.memory_loader import MemoryLoader
from cellmage.storage.memory_store import MemoryStore


def check(condition, message):
    """Check if a condition is True and print result."""
    if condition:
        print(f"✓ {message}")
        return True
    else:
        print(f"✗ {message}")
        return False


def main():
    """Run verification tests on cellmage components."""
    print("\n===== TESTING CELLMAGE LIBRARY =====\n")
    success_count = 0
    total_tests = 0

    # Create components for testing
    memory_loader = MemoryLoader()
    memory_store = MemoryStore()

    # Mock context provider
    context_provider = MagicMock()
    context_provider.get_execution_context.return_value = (1, "test-cell-id")

    # Mock LLM client
    llm_client = MagicMock()
    llm_client.chat.return_value = "This is a mock LLM response"

    print("\n----- Testing Memory Loader -----\n")

    # Add test persona
    memory_loader.add_persona(
        name="test_persona", system_message="You are a test assistant", config={"temperature": 0.7}
    )

    # Add test snippet
    memory_loader.add_snippet(name="test_snippet", content="This is a test snippet")

    # Test persona operations
    total_tests += 1
    success_count += check("test_persona" in memory_loader.list_personas(), "Persona was added successfully")

    persona = memory_loader.get_persona("test_persona")
    total_tests += 1
    success_count += check(
        persona is not None and persona.system_message == "You are a test assistant",
        "Persona can be retrieved and has correct system message",
    )

    # Test snippet operations
    total_tests += 1
    success_count += check("test_snippet" in memory_loader.list_snippets(), "Snippet was added successfully")

    snippet = memory_loader.get_snippet("test_snippet")
    total_tests += 1
    success_count += check(snippet == "This is a test snippet", "Snippet can be retrieved and has correct content")

    print("\n----- Testing Memory Store -----\n")

    # Create test messages and metadata
    messages = [
        Message(role="system", content="System message", id=str(uuid.uuid4())),
        Message(role="user", content="User message", id=str(uuid.uuid4())),
        Message(role="assistant", content="Assistant message", id=str(uuid.uuid4())),
    ]

    metadata = ConversationMetadata(total_messages=len(messages), turns=1)

    # Test saving conversation
    identifier = memory_store.save_conversation(messages, metadata, "test_conversation")
    total_tests += 1
    success_count += check(identifier == "test_conversation", "Conversation saved with correct identifier")

    # Test listing conversations
    conversations = memory_store.list_saved_conversations()
    total_tests += 1
    success_count += check(
        len(conversations) == 1 and conversations[0]["identifier"] == "test_conversation",
        "Conversation listing shows the saved conversation",
    )

    # Test loading conversation
    loaded_messages, loaded_metadata = memory_store.load_conversation("test_conversation")
    total_tests += 1
    success_count += check(
        len(loaded_messages) == len(messages)
        and loaded_messages[0].role == "system"
        and loaded_messages[1].role == "user"
        and loaded_messages[2].role == "assistant",
        "Conversation loaded with correct messages",
    )

    print("\n----- Testing History Manager -----\n")

    # Create history manager
    history_manager = HistoryManager(history_store=memory_store, context_provider=context_provider)

    # Add test messages
    msg1 = Message(role="system", content="System message", id=str(uuid.uuid4()))
    msg2 = Message(role="user", content="User message", id=str(uuid.uuid4()))
    msg3 = Message(role="assistant", content="Assistant message", id=str(uuid.uuid4()))

    history_manager.add_message(msg1)
    history_manager.add_message(msg2)
    history_manager.add_message(msg3)

    # Test history retrieval
    history = history_manager.get_history()
    total_tests += 1
    success_count += check(len(history) == 3, "History manager has correct number of messages")

    # Test cell ID tracking
    total_tests += 1
    success_count += check(
        "test-cell-id" in history_manager.cell_last_history_index, "Cell ID is tracked correctly"
    )

    print("\n----- Testing Chat Manager -----\n")

    # Create chat manager
    chat_manager = ChatManager(
        llm_client=llm_client,
        persona_loader=memory_loader,
        snippet_provider=memory_loader,
        history_store=memory_store,
        context_provider=context_provider,
    )

    # Test persona operations
    personas = chat_manager.list_personas()
    total_tests += 1
    success_count += check("test_persona" in personas, "Chat manager can list personas")

    # Set default persona
    chat_manager.set_default_persona("test_persona")
    total_tests += 1
    success_count += check(llm_client.set_override.called, "Setting persona applies configuration overrides")

    # Test snippet operations
    snippets = chat_manager.list_snippets()
    total_tests += 1
    success_count += check("test_snippet" in snippets, "Chat manager can list snippets")

    chat_manager.add_snippet("test_snippet")
    total_tests += 1
    success_count += check(any(m.is_snippet for m in chat_manager.get_history()), "Snippet was added to history")

    # Test chat functionality - disable streaming for test
    response = chat_manager.chat("Hello world", stream=False)
    total_tests += 1
    success_count += check(response == "This is a mock LLM response", "Chat returns the expected response")

    # Test that LLM client was called
    total_tests += 1
    success_count += check(llm_client.chat.called, "LLM client was called during chat")

    # Check history after chat
    history = chat_manager.get_history()
    total_tests += 1
    success_count += check(len(history) > 0, "Messages were added to history during chat")

    # Print summary
    print("\n===== TEST SUMMARY =====\n")
    print(f"Tests passed: {success_count} out of {total_tests}")
    print(f"Success rate: {success_count / total_tests * 100:.0f}%")

    return 0 if success_count == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
