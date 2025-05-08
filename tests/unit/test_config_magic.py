"""
Unit tests for the refactored config_magic module.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Add the parent directory to the sys.path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from cellmage.magic_commands.ipython.config_handlers import (
    AdapterConfigHandler,
    HistoryDisplayHandler,
    ModelSetupHandler,
    OverrideConfigHandler,
    PersistenceConfigHandler,
    PersonaConfigHandler,
    SnippetConfigHandler,
    StatusDisplayHandler,
)
from cellmage.magic_commands.ipython.config_handlers.base_config_handler import (
    BaseConfigHandler,
)
from cellmage.magic_commands.ipython.config_magic import ConfigMagics


class TestConfigMagicRefactoring:
    """Tests for the refactored config_magic module."""

    def test_handler_initialization(self):
        """Test that the ConfigMagics class initializes with all handlers."""
        magic = ConfigMagics()

        # Check that all handlers are initialized
        assert len(magic.handlers) == 9

        # Check handler types
        handler_types = [type(handler) for handler in magic.handlers]
        assert PersonaConfigHandler in handler_types
        assert SnippetConfigHandler in handler_types
        assert OverrideConfigHandler in handler_types
        assert HistoryDisplayHandler in handler_types
        assert PersistenceConfigHandler in handler_types
        assert ModelSetupHandler in handler_types
        assert AdapterConfigHandler in handler_types
        assert StatusDisplayHandler in handler_types

    @patch(
        "cellmage.magic_commands.ipython.config_handlers.status_display_handler.StatusDisplayHandler._show_status"
    )
    def test_status_as_default(self, mock_show_status):
        """Test that status is shown when no arguments are passed."""
        magic = ConfigMagics()

        # Mock the _get_manager method
        magic._get_manager = MagicMock()

        # Call configure_llm with no arguments
        magic.configure_llm("")

        # Check that status was shown
        mock_show_status.assert_called_once()

    def test_handler_execution(self):
        """Test that all handlers are called in order."""
        # Create mock handlers
        mock_handlers = [MagicMock(spec=BaseConfigHandler) for _ in range(8)]
        for handler in mock_handlers:
            handler.handle_args.return_value = False

        # Create ConfigMagics instance with mock handlers
        magic = ConfigMagics()
        magic.handlers = mock_handlers

        # Mock the _get_manager method
        magic._get_manager = MagicMock()

        # Call configure_llm with empty string
        magic.configure_llm("")

        # Check that all handlers were called
        for handler in mock_handlers:
            handler.handle_args.assert_called_once()
