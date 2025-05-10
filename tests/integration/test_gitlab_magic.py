# filepath: /Users/tpinto/madpin/cellmage/tests/integration/test_gitlab_magic.py
"""
Test the GitLab magic command.
"""

import unittest.mock as mock

import pytest
from IPython.testing.globalipapp import get_ipython, start_ipython

# Skip tests if python-gitlab module is not available
pytest.importorskip("gitlab")


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


def test_gitlab_magic_loads(ip_instance):
    """Test that the GitLab magic command loads correctly."""
    ip = ip_instance

    # Load the extension
    with mock.patch.dict(
        "os.environ", {"GITLAB_URL": "https://gitlab.com", "GITLAB_PAT": "dummy_token"}
    ):
        with mock.patch("cellmage.utils.gitlab_utils.GitLabUtils"):
            ip.run_cell("%load_ext cellmage.integrations.gitlab_magic")

            # Check that the magic command is registered
            assert "gitlab" in ip.magics_manager.magics["line"]


def test_gitlab_fetch_repository(ip_instance):
    """Test fetch_repository functionality."""
    ip = ip_instance

    # Create a mock GitLabUtils instance
    mock_gitlab_utils = mock.MagicMock()

    # Set up the mock to return appropriate data
    mock_repo = {
        "project_info": {
            "name": "test-project",
            "name_with_namespace": "test-namespace/test-project",
            "description": "Test project description",
            "web_url": "https://gitlab.com/test-namespace/test-project",
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
    mock_gitlab_utils.get_repository_summary.return_value = mock_repo
    mock_gitlab_utils.format_repository_for_llm.return_value = "Formatted Repository Content"

    # Set up the environment and mock class
    with mock.patch.dict(
        "os.environ", {"GITLAB_URL": "https://gitlab.com", "GITLAB_PAT": "dummy_token"}
    ):
        with mock.patch("cellmage.utils.gitlab_utils.GitLabUtils", return_value=mock_gitlab_utils):
            # Load the extension
            ip.run_cell("%reload_ext cellmage.integrations.gitlab_magic")

            # Run the magic command
            ip.run_line_magic("gitlab", "test-namespace/test-project --show")

            # Verify the call was made correctly
            mock_gitlab_utils.get_repository_summary.assert_called_once()
            args, kwargs = mock_gitlab_utils.get_repository_summary.call_args
            assert args[0] == "test-namespace/test-project"


def test_gitlab_fetch_merge_request(ip_instance):
    """Test fetch_merge_request functionality."""
    ip = ip_instance

    # Create a mock GitLabUtils instance
    mock_gitlab_utils = mock.MagicMock()

    # Set up the mock to return appropriate data
    mock_project = mock.MagicMock()
    mock_gitlab_utils.get_project.return_value = mock_project

    mock_mr = {
        "id": 123,
        "title": "Test merge request",
        "description": "This is a test description",
        "state": "opened",
        "source_branch": "feature-branch",
        "target_branch": "main",
        "author": {"name": "Author Name", "username": "author_username"},
        "web_url": "https://gitlab.com/test-namespace/test-project/-/merge_requests/123",
        "created_at": "2025-04-28T10:00:00Z",
        "updated_at": "2025-04-29T10:00:00Z",
        "changes": [
            {
                "old_path": "file1.py",
                "new_path": "file1.py",
                "diff": "@@ -1,3 +1,5 @@\n+# Added comment\n def function():\n-    return True\n+    # Modified function\n+    return False",
            }
        ],
    }
    mock_gitlab_utils.get_merge_request.return_value = mock_mr
    mock_gitlab_utils.format_merge_request_for_llm.return_value = "Formatted MR Content"

    # Set up the environment and mock class
    with mock.patch.dict(
        "os.environ", {"GITLAB_URL": "https://gitlab.com", "GITLAB_PAT": "dummy_token"}
    ):
        with mock.patch("cellmage.utils.gitlab_utils.GitLabUtils", return_value=mock_gitlab_utils):
            # Load the extension
            ip.run_cell("%reload_ext cellmage.integrations.gitlab_magic")

            # Run the magic command with MR
            ip.run_line_magic("gitlab", "test-namespace/test-project --mr 123 --show")

            # Verify the calls were made correctly
            mock_gitlab_utils.get_project.assert_called_once_with("test-namespace/test-project")
            mock_gitlab_utils.get_merge_request.assert_called_once_with(mock_project, "123")


def test_gitlab_add_to_history(ip_instance):
    """Test adding a repository to history."""
    ip = ip_instance

    # Create a mock GitLabUtils instance
    mock_gitlab_utils = mock.MagicMock()

    # Set up the mock to return appropriate data
    mock_repo = {
        "project_info": {
            "name": "test-project",
            "name_with_namespace": "test-namespace/test-project",
        },
        "repository_contents": {
            "file_count": 10,
            "code_file_count": 8,
            "total_lines": 500,
        },
    }
    mock_gitlab_utils.get_repository_summary.return_value = mock_repo
    mock_gitlab_utils.format_repository_for_llm.return_value = "Formatted Repository Content"

    # Set up the environment and mock class
    with mock.patch.dict(
        "os.environ", {"GITLAB_URL": "https://gitlab.com", "GITLAB_PAT": "dummy_token"}
    ):
        with mock.patch("cellmage.utils.gitlab_utils.GitLabUtils", return_value=mock_gitlab_utils):
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
                ip.run_cell("%reload_ext cellmage.integrations.gitlab_magic")

                # Run the magic command with system flag
                ip.run_line_magic("gitlab", "test-namespace/test-project --system")

                # Verify the calls were made correctly
                mock_gitlab_utils.get_repository_summary.assert_called_once()
                args, kwargs = mock_gitlab_utils.get_repository_summary.call_args
                assert args[0] == "test-namespace/test-project"

                # Verify the message was added to history
                mock_history_manager.add_message.assert_called_once()
                args, kwargs = mock_history_manager.add_message.call_args
                message = args[0]
                assert message.role == "system"
                assert message.metadata["source"] == "gitlab"
                assert message.metadata["gitlab_id"] == "test-namespace/test-project"
                assert message.metadata["type"] == "repository"
