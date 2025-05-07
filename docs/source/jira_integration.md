# Jira Integration

CellMage provides integration with Jira through the `%jira` magic command, allowing you to fetch Jira tickets directly into your notebook and use them as context for LLM queries.

## Installation

To use the Jira integration, install CellMage with the `jira` extra:

```bash
pip install "cellmage[jira]"
```

## Configuration

The Jira integration requires the following environment variables:

- `JIRA_URL`: The URL of your Jira instance (e.g., `https://your-company.atlassian.net`)
- `JIRA_USER_EMAIL`: The email address associated with your Jira account
- `JIRA_API_TOKEN`: Your Jira API token/personal access token (PAT)

You can set these in a `.env` file in your working directory or directly in your environment:

```bash
# In your terminal
export JIRA_URL="https://your-company.atlassian.net"
export JIRA_USER_EMAIL="your.email@company.com"
export JIRA_API_TOKEN="your_jira_api_token"

# Or in a .env file
JIRA_URL=https://your-company.atlassian.net
JIRA_USER_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_jira_api_token
```

## Basic Usage

To fetch a specific ticket:

```ipython
%jira PROJECT-123
```

This fetches the ticket and adds it as a user message in the chat history.

## Advanced Usage

### Using JQL Queries

You can also use JQL (Jira Query Language) to fetch multiple tickets:

```ipython
%jira --jql "project = PROJECT AND assignee = currentUser() ORDER BY updated DESC" --max 3
```

### Command Options

- `--jql "query"`: Use a JQL query to fetch multiple tickets
- `--max N`: Limit the number of tickets returned by a JQL query (default: 5)
- `--system`: Add tickets as system messages instead of user messages
- `--show`: Only display the tickets without adding them to the chat history

### Examples

Fetch a ticket and add it to history:
```ipython
%jira PROJECT-123
```

Fetch a ticket and add it as system context:
```ipython
%jira PROJECT-123 --system
```

Just view a ticket without adding to history:
```ipython
%jira PROJECT-123 --show
```

Fetch your recent tickets:
```ipython
%jira --jql "assignee = currentUser() ORDER BY updated DESC" --max 5
```

## Using Jira Tickets with LLM Queries

After loading a Jira ticket with `%jira`, you can refer to it in your LLM prompts:

```ipython
# First, fetch a ticket
%jira PROJECT-123

# Then ask the LLM about it
%%llm
Given the Jira ticket above, what are the key requirements I need to implement?
```

This allows you to use Jira tickets as context for your LLM queries, making it easier to work with project-specific information.

## Troubleshooting

### Authentication Issues

If you encounter authentication errors:

1. **Verify your environment variables**:
   ```ipython
   import os
   print("JIRA_URL:", os.environ.get("JIRA_URL"))
   print("JIRA_USER_EMAIL:", os.environ.get("JIRA_USER_EMAIL"))
   print("JIRA_API_TOKEN is set:", os.environ.get("JIRA_API_TOKEN") is not None)
   ```

2. **Check API token validity**:
   - Ensure your API token has not expired
   - Verify you have the correct permissions for the Jira instance
   - Regenerate your token if necessary

### Permission Problems

If you can authenticate but can't access certain tickets:

1. **Verify you have access to the ticket/project** in the Jira web interface
2. **Check for permission restrictions** on the tickets you're trying to access
3. **JQL query permissions**: Ensure you have permission to run the JQL queries you're using

### Other Issues

1. **Connection timeout**: Check your network connection and proxy settings
2. **Rate limiting**: If making many API calls, you may hit rate limits
3. **Empty responses**: Make sure the ticket exists and your JQL query returns results

For persistent issues, examine the CellMage log:

```python
import logging
from cellmage.utils.logging import setup_logging
setup_logging(level=logging.DEBUG)
# The logs will be written to cellmage.log in your working directory
```
