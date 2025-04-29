# Jira Integration

CellMage provides integration with Jira through the `%jira` magic command, allowing you to fetch Jira tickets directly into your notebook and use them as context for LLM queries.

## Installation

To use the Jira integration, install CellMage with the `jira` extra:

```bash
pip install cellmage[jira]
```

## Configuration

The Jira integration requires the following environment variables:

- `JIRA_URL`: The URL of your Jira instance (e.g., `https://your-company.atlassian.net`)
- `JIRA_USER_EMAIL`: The email address associated with your Jira account
- `JIRA_API_TOKEN`: Your Jira API token/personal access token (PAT)

You can set these in a `.env` file in your working directory or directly in your environment.

## Using the `%jira` Magic Command

### Basic Usage

To fetch a specific ticket:

```python
%jira PROJECT-123
```

This fetches the ticket and adds it as a user message in the chat history.

### Using JQL Queries

You can also use JQL (Jira Query Language) to fetch multiple tickets:

```python
%jira --jql 'project = PROJECT AND assignee = currentUser() ORDER BY updated DESC' --max 3
```

### Command Options

- `--jql "query"`: Use a JQL query to fetch multiple tickets
- `--max N`: Limit the number of tickets returned by a JQL query (default: 5)
- `--system`: Add tickets as system messages instead of user messages
- `--show`: Only display the tickets without adding them to the chat history

### Examples

Fetch a ticket and add it to history:
```python
%jira PROJECT-123
```

Fetch a ticket and add it as system context:
```python
%jira PROJECT-123 --system
```

Just view a ticket without adding to history:
```python
%jira PROJECT-123 --show
```

Fetch your recent tickets:
```python
%jira --jql 'assignee = currentUser() ORDER BY updated DESC' --max 5
```

## Using Jira Tickets with LLM Queries

After loading a Jira ticket with `%jira`, you can refer to it in your LLM prompts:

```python
# First, fetch a ticket
%jira PROJECT-123

# Then ask the LLM about it
# The %%llm magic starts a new cell in Jupyter notebooks
%%llm
Given the Jira ticket above, what are the key requirements I need to implement?
```

This allows you to use Jira tickets as context for your LLM queries, making it easier to work with project-specific information.