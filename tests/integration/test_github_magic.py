"""
Test the GitHub magic command.
"""

import unittest.mock as mock

import pytest
from IPython.testing.globalipapp import get_ipython, start_ipython

# Skip tests if PyGithub module is not available
pytest.importorskip("github")


@pytest.fixture(scope="module")
def ip_instance():
    """Start a test IPython kernel."""
    ipython = start_ipython()
    if ipython is None:
        ipython = get_ipython()

    # Make sure we have an IPython instance
    if ipython is None:
        pytest.skip("IPython is not available")

    # Yield the instance for use in tests
    yield ipython


def test_github_magic_loads(ip_instance):
    """Test that the GitHub magic command loads correctly."""
    ip = ip_instance

    # Load the extension
    with mock.patch.dict("os.environ", {"GITHUB_TOKEN": "dummy_token"}):
        with mock.patch("cellmage.utils.github_utils.GitHubUtils"):
            ip.run_cell("%load_ext cellmage.integrations.github_magic")

            # Check that the magic command is registered
            assert "github" in ip.magics_manager.magics["line"]


def test_github_fetch_repository(ip_instance):
    """Test fetch_repository functionality."""
    ip = ip_instance

    # Create a mock GitHubUtils instance
    mock_github_utils = mock.MagicMock()

    # Set up the mock to return appropriate data
    mock_repo = {
        "project_info": {
            "name": "test-repo",
            "full_name": "username/test-repo",
            "description": "Test repo description",
            "web_url": "https://github.com/username/test-repo",
            "default_branch": "main",
            "visibility": "public",
        },
        "repository_contents": {
            "file_count": 10,
            "code_file_count": 8,
            "total_lines": 500,
            "file_breakdown": {
                ".py": 5,
                ".js": 3,
            },
            "top_files": [
                {"path": "file1.py", "lines": 200},
                {"path": "file2.py", "lines": 100},
            ],
        },
        "last_commit": {
            "short_id": "abc123",
            "author_name": "Test Author",
            "committed_date": "2025-04-29T10:00:00Z",
            "message": "Test commit message",
        },
        "contributors": [
            {"name": "Contributor 1", "email": "contributor1@example.com", "commits": 10},
        ],
    }
    mock_github_utils.get_repository_summary.return_value = mock_repo
    mock_github_utils.format_repository_for_llm.return_value = "Formatted Repository Content"

    # Set up the environment and mock class
    with mock.patch.dict("os.environ", {"GITHUB_TOKEN": "dummy_token"}):
        with mock.patch("cellmage.utils.github_utils.GitHubUtils", return_value=mock_github_utils):
            # Load the extension
            ip.run_cell("%reload_ext cellmage.integrations.github_magic")

            # Run the magic command
            ip.run_line_magic("github", "username/test-repo --show")

            # Verify the call was made correctly
            mock_github_utils.get_repository_summary.assert_called_once()
            args, kwargs = mock_github_utils.get_repository_summary.call_args
            assert args[0] == "username/test-repo"


def test_github_fetch_pull_request(ip_instance):
    """Test fetch_pull_request functionality."""
    ip = ip_instance

    # Create a mock GitHubUtils instance
    mock_github_utils = mock.MagicMock()

    # Set up the mock to return appropriate data
    mock_repo = mock.MagicMock()
    mock_github_utils.get_repository.return_value = mock_repo

    mock_pr = {
        "number": 123,
        "title": "Test pull request",
        "description": "This is a test description",
        "state": "open",
        "source_branch": "feature-branch",
        "target_branch": "main",
        "author": {"name": "Author Name", "username": "author_username"},
        "web_url": "https://github.com/username/test-repo/pull/123",
        "created_at": "2025-04-28T10:00:00Z",
        "updated_at": "2025-04-29T10:00:00Z",
        "changes": [
            {
                "old_path": "file1.py",
                "new_path": "file1.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
                "patch": "@@ -1,3 +1,5 @@\n+# Added comment\n def function():\n-    return True\n+    # Modified function\n+    return False",
            }
        ],
    }
    mock_github_utils.get_pull_request.return_value = mock_pr
    mock_github_utils.format_pull_request_for_llm.return_value = "Formatted PR Content"

    # Set up the environment and mock class
    with mock.patch.dict("os.environ", {"GITHUB_TOKEN": "dummy_token"}):
        with mock.patch("cellmage.utils.github_utils.GitHubUtils", return_value=mock_github_utils):
            # Load the extension
            ip.run_cell("%reload_ext cellmage.integrations.github_magic")

            # Run the magic command with PR
            ip.run_line_magic("github", "username/test-repo --pr 123 --show")

            # Verify the calls were made correctly
            mock_github_utils.get_repository.assert_called_once_with("username/test-repo")
            mock_github_utils.get_pull_request.assert_called_once_with(mock_repo, "123")


def test_github_add_to_history(ip_instance):
    """Test adding a repository to history."""
    ip = ip_instance

    # Create a mock GitHubUtils instance
    mock_github_utils = mock.MagicMock()

    # Set up the mock to return appropriate data
    mock_repo = {
        "project_info": {
            "name": "test-repo",
            "full_name": "username/test-repo",
        },
        "repository_contents": {
            "file_count": 10,
            "code_file_count": 8,
            "total_lines": 500,
        },
    }
    mock_github_utils.get_repository_summary.return_value = mock_repo
    mock_github_utils.format_repository_for_llm.return_value = "Formatted Repository Content"

    # Set up the environment and mock class
    with mock.patch.dict("os.environ", {"GITHUB_TOKEN": "dummy_token"}):
        with mock.patch("cellmage.utils.github_utils.GitHubUtils", return_value=mock_github_utils):
            # Need to patch at the module level where the function is called
            with mock.patch(
                "cellmage.magic_commands.ipython.common.get_chat_manager"
            ) as mock_get_manager:
                # Create the mock chat manager structure
                mock_chat_manager = mock.MagicMock()
                mock_history_manager = mock.MagicMock()
                mock_chat_manager.history_manager = mock_history_manager
                mock_get_manager.return_value = mock_chat_manager

                # Load the extension
                ip.run_cell("%reload_ext cellmage.integrations.github_magic")

                # Run the magic command with system flag
                ip.run_line_magic("github", "username/test-repo --system")

                # Verify the calls were made correctly
                mock_github_utils.get_repository_summary.assert_called_once()
                args, kwargs = mock_github_utils.get_repository_summary.call_args
                assert args[0] == "username/test-repo"

                # Verify the message was added to history
                mock_history_manager.add_message.assert_called_once()
                args, kwargs = mock_history_manager.add_message.call_args
                message = args[0]
                assert message.role == "system"
                assert message.metadata["source"] == "github"
                assert message.metadata["github_id"] == "username/test-repo"
                assert message.metadata["type"] == "repository"
