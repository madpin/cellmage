#!/usr/bin/env python
"""
Simple script to test the token counting in context of %llm_config magic.
This simulates a user running both --show-history and --tokens commands.
"""

import logging
from unittest.mock import MagicMock

from cellmage.chat_manager import ChatManager
from cellmage.context_providers.ipython_context_provider import IPythonContextProvider
from cellmage.magic_commands.history import handle_history_commands
from cellmage.magic_commands.ipython.config_handlers.token_count_handler import (
    TokenCountHandler,
)
from cellmage.models import Message

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main():
    print("Testing token counting consistency between --show-history and --tokens")
    logger.info("Starting token consistency test")

    # Create a simple context provider (doesn't need real IPython)
    context_provider = IPythonContextProvider()
    logger.debug("Created context provider")

    # Create a chat manager
    manager = ChatManager(context_provider=context_provider)
    logger.debug("Created chat manager")

    # Override count_tokens_for_messages to simulate accurate token counting
    manager.llm_client = MagicMock()
    manager.llm_client.count_tokens_for_messages = lambda msgs: len(msgs) * 10
    logger.debug("Mocked llm_client.count_tokens_for_messages")

    # Add some messages to the history
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello, how are you?"),
        Message(
            role="assistant",
            content="I'm doing well, thank you for asking! How can I help you today?",
        ),
    ]

    # Directly set the history since add_message might not work in test context
    manager.conversation_manager = MagicMock()
    manager.conversation_manager.get_messages = lambda: messages
    manager.get_history = lambda: messages
    logger.debug(f"Set up mock history with {len(messages)} messages")

    # Create a token count handler
    token_handler = TokenCountHandler()
    logger.debug("Created TokenCountHandler")

    # Create mock args with tokens=True
    args_tokens = MagicMock()
    args_tokens.tokens = True
    args_tokens.token = False
    logger.debug("Created args for token handler")

    # Call token handler's show_token_count method
    print("\n=== Using --tokens ===")
    try:
        token_handler._show_token_count(manager)
        logger.debug("Called token_handler._show_token_count")
    except Exception as e:
        logger.error(f"Error in token handler: {e}", exc_info=True)

    # Get the history command output
    print("\n=== Using --show-history ===")
    try:
        args_history = MagicMock()
        args_history.show_history = True
        args_history.clear_history = False
        handle_history_commands(args_history, manager)
        logger.debug("Called handle_history_commands")
    except Exception as e:
        logger.error(f"Error in history handler: {e}", exc_info=True)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
