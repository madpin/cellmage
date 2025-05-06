"""
Base handler for %llm_config magic command options.

This module provides the base class for all config command handlers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

# Create a logger
logger = logging.getLogger(__name__)


class BaseConfigHandler(ABC):
    """Base class for all config command handlers.

    This abstract base class defines the interface that all config handlers
    should implement. Each specialized handler will inherit from this class
    and implement the handle_args method to process specific arguments.
    """

    @abstractmethod
    def handle_args(self, args: Any, manager: Any) -> bool:
        """
        Handle arguments for the %llm_config magic command.

        Args:
            args: The parsed arguments from the magic command.
            manager: The ChatManager instance.

        Returns:
            bool: True if any action was performed, False otherwise.
        """
        pass
