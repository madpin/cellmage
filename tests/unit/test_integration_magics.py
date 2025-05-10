"""
Tests for the integration magic commands.

This module tests the integration magic commands like GitHub, Confluence, etc.
"""

from unittest.mock import MagicMock, patch

import pytest

from tests.unit.magic_commands.test_base import MagicCommandsTestBase, ipython_required


@pytest.fixture(scope="module")
def ip_shell():
    """Get the current IPython shell for magic command tests."""
    from IPython import get_ipython

    ipython = get_ipython()
    if ipython is None:
        pytest.skip("IPython is not available or not running in an IPython environment")
    yield ipython


class TestBaseMagics(MagicCommandsTestBase):
    """Tests for the BaseMagics class that provides common functionality for all magics."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        # Import the BaseMagics class
        from cellmage.integrations.base_magic import BaseMagics

        self.base_magic = BaseMagics(self.mock_ipython)

    @ipython_required
    def test_get_chat_manager(self):
        """Test that _get_chat_manager returns the correct manager."""
        # Call the method
        manager = self.base_magic._get_chat_manager()

        # Verify the correct manager was returned
        self.assertEqual(manager, self.mock_manager)

    @ipython_required
    def test_get_execution_context(self):
        """Test that _get_execution_context returns the correct context."""
        exec_count = 42
        cell_id = "test_cell_123"
        mock_context_provider = MagicMock()
        mock_context_provider.get_execution_context.return_value = (exec_count, cell_id)
        with patch(
            "cellmage.context_providers.ipython_context_provider.get_ipython_context_provider",
            return_value=mock_context_provider,
        ):
            result = self.base_magic._get_execution_context()
        self.assertEqual(result, (exec_count, cell_id))

    @ipython_required
    def test_add_to_history(self):
        """Test that _add_to_history adds content to history correctly."""
        content = "Test content"
        source_type = "test"
        source_id = "123"
        source_name = "test_source"
        id_key = "test_id"
        # Patch context provider to return a tuple
        mock_context_provider = MagicMock()
        mock_context_provider.get_execution_context.return_value = (1, "cellid")
        with patch(
            "cellmage.context_providers.ipython_context_provider.get_ipython_context_provider",
            return_value=mock_context_provider,
        ):
            result = self.base_magic._add_to_history(
                content, source_type, source_id, source_name, id_key
            )
        self.mock_manager.history_manager.add_message.assert_called_once()
        self.assertTrue(result)

    @ipython_required
    def test_find_messages_to_remove(self):
        """Test that _find_messages_to_remove finds the correct messages."""
        # Set up test parameters
        source_type = "test"
        source_id = "123"
        source_name = "test_source"
        id_key = "test_id"

        # Create mock history with matching and non-matching messages
        mock_history = [
            MagicMock(metadata={"source": source_name, id_key: source_id, "type": source_type}),
            MagicMock(metadata={"source": "other_source", id_key: "456", "type": "other"}),
            MagicMock(metadata={"source": source_name, id_key: source_id, "type": source_type}),
        ]

        # Call the method
        indices = self.base_magic._find_messages_to_remove(
            mock_history, source_name, source_type, source_id, id_key
        )

        # Verify the correct indices were returned (0 and 2)
        self.assertEqual(indices, [0, 2])


class MockIntegrationMagic:
    """Base class for testing integration magic commands."""

    def setup_magic_class(self, magic_module_path, magic_class_name, ipython_shell):
        """Set up a magic class for testing with a real IPython shell."""
        try:
            import importlib

            module = importlib.import_module(magic_module_path)
            magic_class = getattr(module, magic_class_name)
            magic_instance = magic_class(ipython_shell)
            return magic_instance
        except ImportError:
            pytest.skip(f"Module {magic_module_path} not available")
            return None


class TestGitHubMagic(MagicCommandsTestBase, MockIntegrationMagic):
    """Tests for the GitHub magic command."""

    @pytest.fixture(autouse=True)
    def _setup_ip(self, ip_shell):
        self.ipython = ip_shell

    def setUp(self):
        """Set up test environment."""
        MagicCommandsTestBase.setUp(self)

        # Use the real IPython shell for magics
        with patch("cellmage.integrations.github_magic.magics_class", lambda cls: cls):
            with patch("cellmage.integrations.github_magic.line_magic", lambda func: func):
                with patch(
                    "cellmage.integrations.github_magic.magic_arguments", lambda: lambda func: func
                ):
                    with patch(
                        "cellmage.integrations.github_magic.argument",
                        lambda *args, **kwargs: lambda func: func,
                    ):
                        from cellmage.integrations.github_magic import GitHubMagics

                        self.github_magic = GitHubMagics(self.ipython)

    @ipython_required
    @patch("cellmage.integrations.base_magic.BaseMagics._add_to_history")
    @patch("cellmage.utils.github_utils.GitHubUtils")
    def test_github_magic_calls_add_to_history(self, mock_github_utils_class, mock_add_to_history):
        """Test that the GitHub magic calls _add_to_history correctly."""
        mock_github_utils = MagicMock()
        mock_github_utils.get_issue.return_value = "Test issue content"
        mock_github_utils_class.return_value = mock_github_utils
        self.github_magic.github_magic("user/repo --issue 123")
        mock_add_to_history.assert_called_once()
        content = mock_add_to_history.call_args[0][0]
        self.assertIn("Test issue content", content)


class TestConfluenceMagic(MagicCommandsTestBase, MockIntegrationMagic):
    """Tests for the Confluence magic command."""

    @pytest.fixture(autouse=True)
    def _setup_ip(self, ip_shell):
        self.ipython = ip_shell

    def setUp(self):
        """Set up test environment."""
        MagicCommandsTestBase.setUp(self)

        # Use the real IPython shell for magics
        with patch("cellmage.integrations.confluence_magic.magics_class", lambda cls: cls):
            with patch("cellmage.integrations.confluence_magic.line_magic", lambda func: func):
                with patch(
                    "cellmage.integrations.confluence_magic.magic_arguments",
                    lambda: lambda func: func,
                ):
                    with patch(
                        "cellmage.integrations.confluence_magic.argument",
                        lambda *args, **kwargs: lambda func: func,
                    ):
                        # Import the magic class
                        from cellmage.integrations.confluence_magic import (
                            ConfluenceMagics,
                        )

                        self.confluence_magic = ConfluenceMagics(self.ipython)

    @ipython_required
    @patch("cellmage.integrations.base_magic.BaseMagics._add_to_history")
    @patch("cellmage.utils.confluence_utils.ConfluenceClient")
    def test_confluence_magic_calls_add_to_history(
        self, mock_confluence_client_class, mock_add_to_history
    ):
        """Test that the Confluence magic calls _add_to_history correctly."""
        mock_confluence = MagicMock()
        mock_confluence.get_page_by_id.return_value = {
            "id": "123",
            "title": "Test Page",
            "body": {"storage": {"value": "Test content"}},
        }
        mock_confluence_client_class.return_value = mock_confluence
        self.confluence_magic.confluence_magic("123")
        mock_add_to_history.assert_called_once()
        content = mock_add_to_history.call_args[0][0]
        self.assertIn("Test content", content)


if __name__ == "__main__":
    pytest.main([__file__])
