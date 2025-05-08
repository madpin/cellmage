"""
Unit tests for the refactored magic commands.

This module contains tests for the new magic command structure.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

import pytest


class TestMagicCommands(unittest.TestCase):
    """Test the refactored magic commands structure and functionality."""

    def setUp(self):
        """Set up test environment."""
        # Skip tests if IPython is not available
        try:
            import IPython  # noqa: F401

            self.ipython_available = True
        except ImportError:
            self.ipython_available = False
            self.skipTest("IPython not available")

    @patch("cellmage.magic_commands.ipython.load_magics")
    def test_magic_commands_loading(self, mock_load_magics):
        """Test that the magic command loader properly calls the IPython magic loader."""
        # Import the module under test
        from cellmage.magic_commands import load_ipython_extension

        # Create mock IPython shell
        mock_shell = MagicMock()

        # Call the function under test
        load_ipython_extension(mock_shell)

        # Verify the expected function was called with the shell
        mock_load_magics.assert_called_once_with(mock_shell)

    @patch("cellmage.magic_commands.ipython.common._init_default_manager")
    def test_chat_manager_initialization(self, mock_init_manager):
        """Test that the chat manager is initialized when needed."""
        # Skip if IPython is not available
        if not self.ipython_available:
            self.skipTest("IPython not available")

        # Set up mock return value
        mock_manager = MagicMock()
        mock_init_manager.return_value = mock_manager

        # Reset the global _chat_manager_instance to ensure initialization happens
        import cellmage.magic_commands.ipython.common

        cellmage.magic_commands.ipython.common._chat_manager_instance = None

        # Import the module under test
        from cellmage.magic_commands.ipython.common import get_chat_manager

        # Call the function under test
        manager = get_chat_manager()

        # Verify the manager was initialized
        mock_init_manager.assert_called_once()
        self.assertEqual(manager, mock_manager)

    @pytest.mark.skipif("IPython" not in sys.modules, reason="IPython not available")
    def test_magic_classes_structure(self):
        """Test that all expected magic classes are available with correct structure."""
        # Import the modules under test
        from cellmage.magic_commands.ipython.ambient_magic import AmbientModeMagics
        from cellmage.magic_commands.ipython.config_magic import ConfigMagics
        from cellmage.magic_commands.ipython.llm_magic import CoreLLMMagics

        # Check that they have the expected magic methods
        self.assertTrue(hasattr(CoreLLMMagics, "execute_llm"))
        self.assertTrue(hasattr(ConfigMagics, "configure_llm"))
        self.assertTrue(hasattr(AmbientModeMagics, "configure_llm_persistent"))
        self.assertTrue(hasattr(AmbientModeMagics, "disable_llm_config_persistent"))
        self.assertTrue(hasattr(AmbientModeMagics, "execute_python"))
        self.assertTrue(hasattr(AmbientModeMagics, "process_cell_as_prompt"))
        self.assertTrue(
            hasattr(AmbientModeMagics, "llm_magic"),
            "AmbientModeMagics should have llm_magic method",
        )


if __name__ == "__main__":
    unittest.main()
