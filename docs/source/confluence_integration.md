# Confluence Integration

CellMage provides seamless integration with Atlassian Confluence, allowing you to fetch wiki pages directly into your Jupyter notebooks and use them as context for your LLM prompts.

## Installation

To use the Confluence integration, install CellMage with the `confluence` extra:

```bash
pip install "cellmage[confluence]"
```

## Configuration

The Confluence integration requires the following environment variables:

- `CONFLUENCE_URL`: The URL of your Confluence instance
- `JIRA_USER_EMAIL`: The email address associated with your Atlassian account
- `JIRA_API_TOKEN`: Your Atlassian API token

**Note on `CONFLUENCE_URL` vs `JIRA_URL`**:
- Use `CONFLUENCE_URL` if your Confluence instance has a separate URL from Jira
- If your Confluence is part of your Jira instance (common in Atlassian Cloud), you can use `JIRA_URL` instead
- The integration will check for `CONFLUENCE_URL` first, and if not found, fall back to `JIRA_URL`

You can set these in a `.env` file in your working directory or directly in your environment:

```bash
# In your terminal
export CONFLUENCE_URL="https://your-company.atlassian.net/wiki"
export JIRA_USER_EMAIL="your.email@company.com"
export JIRA_API_TOKEN="your_atlassian_api_token"

# Or in a .env file
CONFLUENCE_URL=https://your-company.atlassian.net/wiki
JIRA_USER_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_atlassian_api_token
```

To create an Atlassian API token:
- Go to https://id.atlassian.com/manage-profile/security/api-tokens
- Click "Create API token"
- Give it a meaningful label and copy the token value

## Basic Usage

Load the extension in your Jupyter notebook:

```ipython
%load_ext cellmage.integrations.confluence_magic
```

This will register the `%confluence` magic command.

To fetch a specific Confluence page by its space key and title:

```ipython
%confluence SPACE:Page Title
```

Or by its page ID:

```ipython
%confluence 123456789
```

This will automatically add the page content to your conversation history as a user message, making it available as context for your LLM prompts.

## Advanced Usage

### Format Options

By default, content is converted to Markdown format, which is ideal for LLMs. If you prefer plain text format instead, use the `--text` flag:

```ipython
%confluence SPACE:Page Title --text
```

### Search with CQL

You can search for pages using Confluence Query Language (CQL):

```ipython
%confluence --cql "space = SPACE AND title ~ 'Search Term'"
```

By default, this returns up to 5 results. You can adjust this with the `--max` parameter:

```ipython
%confluence --cql "space = SPACE AND title ~ 'Search Term'" --max 10
```

### Content Options for CQL Search

When performing a CQL search, you have several content options:

```ipython
# Include full content of each search result (additional API calls)
%confluence --cql "space = DOCS AND text ~ 'api'" --content

# Only include metadata (titles, space, IDs) without page content
%confluence --cql "space = DOCS AND text ~ 'api'" --no-content
```

### Command Options

| Option | Description |
|--------|-------------|
| `--system` | Add the content as a system message instead of a user message |
| `--show` | Just display the content without adding it to conversation history |
| `--text` | Use plain text format instead of Markdown (Markdown is default) |
| `--content` | For CQL search, fetch the full content of each page (additional API calls) |
| `--no-content` | For CQL search, return only metadata without page content |
| `--max N` | Maximum number of results to return for CQL searches (default: 5) |

### Examples

Fetch a specific page (already in Markdown format by default):
```ipython
%confluence DOCS:Project Overview
```

Search for relevant pages without content:
```ipython
%confluence --cql "space = DOCS AND title ~ 'API'" --no-content --show
```

Fetch a specific page and use as system context:
```ipython
%confluence DOCS:API Reference --system
```

## Using Confluence Content with LLM Queries

After fetching a Confluence page, you can refer to it in your LLM prompts:

```ipython
# First, fetch a specific page
%confluence DOCS:Project Overview

# Then ask the LLM about it
%%llm
Based on the Project Overview page, what are the key milestones?
```

You can also combine Confluence content with other integrations:

```ipython
# Fetch project requirements from Confluence
%confluence PROJ:Requirements --system

# Fetch a specific Jira ticket
%jira PROJECT-123

# Ask LLM to analyze both
%%llm
Given the project requirements from Confluence and the Jira ticket above,
what should be our implementation approach?
```

## Troubleshooting

### Authentication Issues

1. **Verify your environment variables**:
   ```ipython
   import os
   print("CONFLUENCE_URL:", os.environ.get("CONFLUENCE_URL"))
   print("JIRA_URL (fallback):", os.environ.get("JIRA_URL"))
   print("JIRA_USER_EMAIL:", os.environ.get("JIRA_USER_EMAIL"))
   print("JIRA_API_TOKEN is set:", os.environ.get("JIRA_API_TOKEN") is not None)
   ```

2. **Check Atlassian API token**:
   - Ensure your Atlassian API token has not expired
   - Verify you created the token with the correct account
   - Regenerate the token if necessary

3. **URL configuration**:
   - Make sure you're using the correct URL format
   - For Atlassian Cloud, it's typically `https://your-company.atlassian.net/wiki`
   - For self-hosted instances, check with your administrator for the correct URL

### Access Permission Issues

1. **Page not found errors**:
   - Verify you have access to the space and page in the Confluence web interface
   - Check if the page still exists or has been moved/renamed
   - Spaces and page titles are case-sensitive

2. **Space permissions**:
   - Ensure your account has access to the space you're trying to access
   - Some spaces may be restricted to certain groups or users

### Content Retrieval Issues

1. **Special characters in titles**:
   - If a page title has special characters, try using the page ID instead
   - Find the page ID in the URL when viewing the page (e.g., `pageId=123456789`)

2. **CQL search problems**:
   - Verify your CQL syntax is correct
   - Try simpler queries first, then add complexity
   - Enclose queries with special characters in quotes

3. **Content formatting issues**:
   - Some complex Confluence pages may not convert to Markdown perfectly
   - Try using `--text` if Markdown conversion causes issues

For persistent issues, enable debug logging:

```ipython
import logging
from cellmage.utils.logging import setup_logging
setup_logging(level=logging.DEBUG)
# The logs will be written to cellmage.log in your working directory
```
