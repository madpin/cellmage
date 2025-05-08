"""
Configuration handlers for the %llm_config magic command.

This package contains specialized handlers for different aspects of the %llm_config
magic command, each responsible for a specific group of related sub-options.
"""

from .adapter_config_handler import AdapterConfigHandler

# Import all handlers to make them available through the package
from .base_config_handler import BaseConfigHandler
from .history_display_handler import HistoryDisplayHandler
from .model_setup_handler import ModelSetupHandler
from .override_config_handler import OverrideConfigHandler
from .persistence_config_handler import PersistenceConfigHandler
from .persona_config_handler import PersonaConfigHandler
from .snippet_config_handler import SnippetConfigHandler
from .status_display_handler import StatusDisplayHandler
from .token_count_handler import TokenCountHandler

__all__ = [
    "BaseConfigHandler",
    "PersonaConfigHandler",
    "SnippetConfigHandler",
    "OverrideConfigHandler",
    "HistoryDisplayHandler",
    "PersistenceConfigHandler",
    "ModelSetupHandler",
    "AdapterConfigHandler",
    "StatusDisplayHandler",
    "TokenCountHandler",
]
