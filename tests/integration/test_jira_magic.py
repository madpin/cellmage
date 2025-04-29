"""
Test the Jira magic command.
"""

import unittest.mock as mock

import pytest
from IPython.testing.globalipapp import get_ipython, start_ipython

# Skip tests if jira module is not available
pytest.importorskip("jira")


@pytest.fixture(scope="module")
def ip():
    """Start a test IPython kernel."""
    ipython = start_ipython()
    if ipython is None:
        ipython = get_ipython()

    # Make sure we have an IPython instance
    if ipython is None:
        pytest.skip("IPython is not available")

    # Yield the instance for use in tests
    yield ipython


def test_jira_magic_loads(ip):
    """Test that the Jira magic command loads correctly."""
    # Load the extension
    ip.run_cell("%load_ext cellmage.integrations.jira_magic")

    # Check that the magic command is registered
    assert "jira" in ip.magics_manager.magics["line"]


@mock.patch("cellmage.integrations.jira_magic.JiraMagics._fetch_ticket")
def test_jira_fetch_ticket(mock_fetch_ticket, ip):
    """Test fetch_ticket functionality."""
    # Mock the fetch_ticket method to return a dummy ticket
    mock_ticket = {
        "key": "TEST-123",
        "summary": "Test ticket",
        "description": "This is a test description",
        "status": "Open",
        "assignee": "Test User",
        "reporter": "Another User",
    }
    mock_fetch_ticket.return_value = mock_ticket

    # Load the extension
    ip.run_cell("%load_ext cellmage.integrations.jira_magic")

    # Run the magic command
    ip.run_line_magic("jira", "TEST-123 --show")

    # Check that the fetch_ticket method was called with the correct ticket key
    mock_fetch_ticket.assert_called_once_with("TEST-123")


@mock.patch("cellmage.integrations.jira_magic.JiraMagics._fetch_tickets_by_jql")
def test_jira_fetch_by_jql(mock_fetch_by_jql, ip):
    """Test fetch_tickets_by_jql functionality."""
    # Mock the fetch_tickets_by_jql method to return dummy tickets
    mock_tickets = [
        {
            "key": "TEST-123",
            "summary": "Test ticket 1",
            "description": "Description 1",
            "status": "Open",
        },
        {
            "key": "TEST-124",
            "summary": "Test ticket 2",
            "description": "Description 2",
            "status": "In Progress",
        },
    ]
    mock_fetch_by_jql.return_value = mock_tickets

    # Load the extension
    ip.run_cell("%load_ext cellmage.integrations.jira_magic")

    # Run the magic command with JQL
    jql_query = "project = TEST AND assignee = currentUser()"
    ip.run_line_magic("jira", f'--jql "{jql_query}" --max 2 --show')

    # Check that the fetch_tickets_by_jql method was called with the correct arguments
    mock_fetch_by_jql.assert_called_once_with(jql_query, max_results=2)


@mock.patch("cellmage.integrations.jira_magic.JiraMagics._add_ticket_to_history")
@mock.patch("cellmage.integrations.jira_magic.JiraMagics._fetch_ticket")
def test_jira_add_to_history(mock_fetch_ticket, mock_add_to_history, ip):
    """Test adding a ticket to history."""
    # Mock the fetch_ticket method to return a dummy ticket
    mock_ticket = {
        "key": "TEST-123",
        "summary": "Test ticket",
        "description": "This is a test description",
        "status": "Open",
    }
    mock_fetch_ticket.return_value = mock_ticket
    mock_add_to_history.return_value = True

    # Load the extension
    ip.run_cell("%load_ext cellmage.integrations.jira_magic")

    # Run the magic command with system flag
    ip.run_line_magic("jira", "TEST-123 --system")

    # Check that the methods were called with the correct arguments
    mock_fetch_ticket.assert_called_once_with("TEST-123")
    mock_add_to_history.assert_called_once_with(mock_ticket, as_system_msg=True)
