"""
Test the GitLab magic command.
"""

import unittest.mock as mock

import pytest
from IPython.testing.globalipapp import start_ipython

# Skip tests if python-gitlab module is not available
pytest.importorskip("gitlab")


@pytest.fixture
def ip():
    """Start a test IPython kernel."""
    return start_ipython()


def test_gitlab_magic_loads(ip):
    """Test that the GitLab magic command loads correctly."""
    # Load the extension
    ip.run_cell("%load_ext cellmage.integrations.gitlab_magic")

    # Check that the magic command is registered
    assert "gitlab" in ip.magics_manager.magics["line"]


@mock.patch("cellmage.integrations.gitlab_magic.GitLabMagics._fetch_repository")
def test_gitlab_fetch_repository(mock_fetch_repository, ip):
    """Test fetch_repository functionality."""
    # Mock the fetch_repository method to return a dummy repository
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
    mock_fetch_repository.return_value = mock_repo

    # Load the extension
    ip.run_cell("%load_ext cellmage.integrations.gitlab_magic")

    # Run the magic command
    ip.run_line_magic("gitlab", "test-namespace/test-project --show")

    # Check that the fetch_repository method was called with the correct project identifier
    mock_fetch_repository.assert_called_once_with("test-namespace/test-project")


@mock.patch("cellmage.integrations.gitlab_magic.GitLabMagics._fetch_merge_request")
def test_gitlab_fetch_merge_request(mock_fetch_mr, ip):
    """Test fetch_merge_request functionality."""
    # Mock the fetch_merge_request method to return a dummy MR
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
    mock_fetch_mr.return_value = mock_mr

    # Load the extension
    ip.run_cell("%load_ext cellmage.integrations.gitlab_magic")

    # Run the magic command with MR
    ip.run_line_magic("gitlab", "test-namespace/test-project --mr 123 --show")

    # Check that the fetch_merge_request method was called with the correct arguments
    mock_fetch_mr.assert_called_once_with("test-namespace/test-project", "123")


@mock.patch("cellmage.integrations.gitlab_magic.GitLabMagics._add_to_history")
@mock.patch("cellmage.integrations.gitlab_magic.GitLabMagics._fetch_repository")
def test_gitlab_add_to_history(mock_fetch_repository, mock_add_to_history, ip):
    """Test adding a repository to history."""
    # Mock the fetch_repository method to return a dummy repository
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
    mock_fetch_repository.return_value = mock_repo
    mock_add_to_history.return_value = True

    # Load the extension
    ip.run_cell("%load_ext cellmage.integrations.gitlab_magic")

    # Run the magic command with system flag
    ip.run_line_magic("gitlab", "test-namespace/test-project --system")

    # Check that the methods were called with the correct arguments
    mock_fetch_repository.assert_called_once_with("test-namespace/test-project")

    # The first argument will be the formatted repository content which is a string
    # We can't easily check the exact content, so we just check that it was called
    # with the correct source_type, source_id, and as_system_msg
    args, kwargs = mock_add_to_history.call_args
    assert kwargs["source_type"] == "repository"
    assert kwargs["source_id"] == "test-namespace/test-project"
    assert kwargs["as_system_msg"]
