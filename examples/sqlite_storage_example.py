#!/usr/bin/env python
"""
CellMage SQLite Storage Example

This example demonstrates how to use the CellMage SQLite storage features
for conversation management and persistence.

Usage:
    python sqlite_storage_example.py

This script shows how to:
1. Initialize a ConversationManager with SQLite storage
2. Add and retrieve messages
3. Save and load conversations
4. Search and tag conversations
5. Generate statistics about stored conversations
"""

import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import cellmage
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cellmage.conversation_manager import ConversationManager
from cellmage.magic_commands import persistence
from cellmage.models import Message
from cellmage.storage.sqlite_store import SQLiteStore

# Create a db file in a temporary location for this example
DB_PATH = Path.home() / ".cellmage" / "examples" / "example_conversation.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def print_section_header(title):
    """Print a section header with nice formatting."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def main():
    """Run the example code demonstrating SQLite storage functionality."""
    print_section_header("CellMage SQLite Storage Example")
    print(f"Using database at: {DB_PATH}")

    # Initialize the conversation manager with SQLite storage
    manager = ConversationManager(db_path=str(DB_PATH))
    print(f"Created new conversation with ID: {manager.current_conversation_id}")

    # Example 1: Add messages to the conversation
    print_section_header("Example 1: Adding Messages")

    # Add a system message
    system_msg = Message(
        role="system",
        content="You are a helpful assistant.",
    )
    manager.add_message(system_msg)
    print("Added system message")

    # Add a user message
    user_msg = Message(
        role="user",
        content="What is the capital of France?",
    )
    manager.add_message(user_msg)
    print("Added user message")

    # Add an assistant message
    assistant_msg = Message(
        role="assistant",
        content="The capital of France is Paris. It's known as the 'City of Light' and is famous for its art, culture, and landmarks like the Eiffel Tower.",
        metadata={"model_used": "gpt-4", "tokens_in": 15, "tokens_out": 34, "cost_str": "$0.002"},
    )
    manager.add_message(assistant_msg)
    print("Added assistant message")

    # Show current messages
    messages = manager.get_messages()
    print(f"\nConversation now has {len(messages)} messages:")
    for i, msg in enumerate(messages):
        preview = (
            msg.content.replace("\n", " ")[:50] + "..." if len(msg.content) > 50 else msg.content
        )
        print(f"  {i + 1}. [{msg.role.upper()}] {preview}")

    # Example 2: Save and create a new conversation
    print_section_header("Example 2: Creating a New Conversation")

    # The current conversation is automatically saved when creating a new one
    new_id = manager.create_new_conversation()
    print(f"Created new conversation with ID: {new_id}")

    # Add a few messages to the new conversation
    manager.add_message(Message(role="system", content="You are a coding assistant."))
    manager.add_message(Message(role="user", content="How do I read a file in Python?"))
    manager.add_message(
        Message(
            role="assistant",
            content="To read a file in Python, you can use the built-in `open()` function:\n\n```python\nwith open('filename.txt', 'r') as file:\n    content = file.read()\n    print(content)\n```\n\nThis opens the file, reads its contents, and then closes it automatically.",
            metadata={
                "model_used": "gpt-4",
                "tokens_in": 12,
                "tokens_out": 50,
                "cost_str": "$0.003",
            },
        )
    )

    print(f"Added 3 messages to conversation {new_id}")

    # Example 3: List all conversations
    print_section_header("Example 3: Listing Saved Conversations")

    # Use the SQLiteStore directly to list saved conversations
    store = SQLiteStore(db_path=str(DB_PATH))
    conversations = store.list_saved_conversations()

    print(f"Found {len(conversations)} saved conversations:")
    for i, conv in enumerate(conversations):
        name = conv.get("name", "Unnamed")
        id_preview = conv.get("id", "unknown")[:8] + "..."
        msg_count = conv.get("message_count", 0)
        timestamp = conv.get("timestamp", 0)
        date_str = (
            datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M") if timestamp else "unknown"
        )

        print(f"  {i + 1}. {name} (ID: {id_preview})")
        print(f"     Date: {date_str}")
        print(f"     Messages: {msg_count}")
        if "model_name" in conv and conv["model_name"]:
            print(f"     Model: {conv['model_name']}")
        print()

    # Example 4: Loading a conversation by ID
    print_section_header("Example 4: Loading a Conversation")

    # Load the first conversation
    if conversations:
        first_conv_id = conversations[0]["id"]
        success = manager.load_conversation(first_conv_id)

        if success:
            messages = manager.get_messages()
            print(f"Loaded conversation {first_conv_id} with {len(messages)} messages:")
            for i, msg in enumerate(messages):
                preview = msg.content.replace("\n", " ")[:50]
                if len(msg.content) > 50:
                    preview += "..."
                print(f"  {i + 1}. [{msg.role.upper()}] {preview}")
        else:
            print(f"Failed to load conversation {first_conv_id}")
    else:
        print("No conversations found to load")

    # Example 5: Adding tags to conversations
    print_section_header("Example 5: Using Tags")

    if conversations:
        # Add a tag to the current conversation
        curr_id = manager.current_conversation_id
        store.add_tag(curr_id, "example")
        store.add_tag(curr_id, "python")

        print(f"Added tags 'example' and 'python' to conversation {curr_id}")

        # Show the updated conversation with tags
        tagged_conversations = store.list_saved_conversations()
        for conv in tagged_conversations:
            if conv["id"] == curr_id:
                tags = conv.get("tags", [])
                print(f"Conversation {curr_id[:8]}... now has tags: {', '.join(tags)}")
                break

    # Example 6: Searching conversations
    print_section_header("Example 6: Searching Conversations")

    # Search for conversations containing "capital"
    search_term = "capital"
    results = store.search_conversations(search_term)

    print(f"Search results for '{search_term}':")
    if results:
        for i, conv in enumerate(results):
            print(
                f"  {i + 1}. {conv.get('name', 'Unnamed')} (ID: {conv.get('id', 'unknown')[:8]}...)"
            )
            print(f"     Messages: {conv.get('message_count', 0)}")
            print(f"     Match: {conv.get('match_context', 'No context')}")
            print()
    else:
        print("  No matching conversations found")

    # Example 7: Getting statistics
    print_section_header("Example 7: Statistics")

    # Get statistics about all stored conversations
    stats = store.get_statistics()

    print("Statistics about stored conversations:")
    print(f"  • Total conversations: {stats.get('total_conversations', 0)}")
    print(f"  • Total messages: {stats.get('total_messages', 0)}")

    if "total_tokens" in stats:
        print(f"  • Total tokens: {stats.get('total_tokens', 0):,}")

    if "messages_by_role" in stats:
        print("  • Messages by role:")
        for role, count in stats["messages_by_role"].items():
            print(f"    - {role}: {count}")

    # Example 8: Exporting to markdown
    print_section_header("Example 8: Exporting to Markdown")

    # Create an export directory
    export_dir = Path.home() / ".cellmage" / "examples" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"conversation_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    # Export the current conversation
    export_path_str = persistence.export_conversation_to_markdown(
        manager, filepath=str(export_path)
    )

    if export_path_str:
        print(f"Conversation exported successfully to: {export_path_str}")
    else:
        print("Failed to export conversation")

    print("\nExample completed. Database saved at:", DB_PATH)


if __name__ == "__main__":
    main()
