#!/usr/bin/env python
"""
Simple script to test the token counting fix.
"""

from unittest.mock import MagicMock

from cellmage.chat_manager import ChatManager
from cellmage.context_providers.ipython_context_provider import IPythonContextProvider
from cellmage.models import Message
from cellmage.utils.message_token_utils import get_token_counts


def main():
    # Create a simple context provider (doesn't need real IPython)
    context_provider = IPythonContextProvider()

    # Create a chat manager
    manager = ChatManager(context_provider=context_provider)

    # Create some test messages
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello, how are you?"),
        Message(
            role="assistant",
            content="I'm doing well, thank you for asking! How can I help you today?",
        ),
    ]

    # Set up the manager to return our messages without actually adding them
    manager.conversation_manager = MagicMock()
    manager.conversation_manager.get_messages = lambda: messages
    manager.get_history = lambda: messages

    # Get the history
    history = manager.get_history()

    # Get token counts
    token_data = get_token_counts(manager, history)

    print("\nToken count using get_token_counts:")
    print(f"Total: {token_data['total']}")
    print(f"User: {token_data['user']}")
    print(f"System: {token_data['system']}")
    print(f"Assistant: {token_data['assistant']}")

    # Calculate token counts manually from metadata
    manual_total = 0
    manual_in = 0
    manual_out = 0

    for msg in history:
        if msg.metadata:
            manual_in += msg.metadata.get("tokens_in", 0)
            manual_out += msg.metadata.get("tokens_out", 0)
            msg_total = msg.metadata.get("total_tokens", 0)
            if msg_total > 0:
                manual_total += msg_total

    if manual_total == 0:
        manual_total = manual_in + manual_out

    print("\nToken count from metadata:")
    print(f"Total: {manual_total}")
    print(f"Input: {manual_in}")
    print(f"Output: {manual_out}")


if __name__ == "__main__":
    main()
