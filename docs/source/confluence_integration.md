# Confluence Integration

CellMage provides seamless integration with Atlassian Confluence, allowing you to fetch wiki pages directly into your Jupyter notebooks and use them as context for your LLM prompts.

## Prerequisites

To use the Confluence integration, you need:

1. Access to a Confluence instance
2. Valid credentials (email/username and API token)
3. The following environment variables set:
   - `CONFLUENCE_URL` (or `JIRA_URL` if your Confluence is part of your Jira instance)
   - `JIRA_USER_EMAIL` 
   - `JIRA_API_TOKEN` 

## Getting Started

Load the extension in your Jupyter notebook:

```python
%load_ext cellmage.integrations.confluence_magic
```

This will register the `%confluence` magic command.

## Fetching Confluence Pages

You can fetch a specific Confluence page by its space key and title:

```python
%confluence SPACE:Page Title
```

Or by its page ID:

```python
%confluence 123456789
```

This will automatically add the page content to your conversation history as a user message, making it available as context for your LLM prompts. Content is converted to Markdown format by default for better LLM comprehension.

### Format Options

By default, content is converted to Markdown format, which is ideal for LLMs. If you prefer plain text format instead, use the `--text` flag:

```python
%confluence SPACE:Page Title --text
```

## Search Confluence with CQL

You can search for pages using Confluence Query Language (CQL):

```python
%confluence --cql "space = SPACE AND title ~ 'Search Term'"
```

By default, this returns up to 5 results. You can adjust this with the `--max` parameter:

```python
%confluence --cql "space = SPACE AND title ~ 'Search Term'" --max 10
```

### Content Options for CQL Search

When performing a CQL search, you have several content options:

```python
# Include full content of each search result (additional API calls)
%confluence --cql "space = DOCS AND text ~ 'api'" --content

# Only include metadata (titles, space, IDs) without page content
%confluence --cql "space = DOCS AND text ~ 'api'" --no-content
```

The `--content` flag is especially useful when you want to get the complete content of each page returned by your search, not just what the search result provides. This makes additional API calls to fetch the full content of each page.

## Additional Options

| Option | Description |
|--------|-------------|
| `--system` | Add the content as a system message instead of a user message |
| `--show` | Just display the content without adding it to conversation history |
| `--text` | Use plain text format instead of Markdown (Markdown is default) |
| `--content` | For CQL search, fetch the full content of each page (additional API calls) |
| `--no-content` | For CQL search, return only metadata without page content |
| `--max N` | Maximum number of results to return for CQL searches (default: 5) |

## Using Confluence Content with LLM Queries

After fetching a Confluence page:

```python
%confluence SPACE:MyPage
```

You can refer to it in your LLM prompts:

```python
%%llm
Given the Confluence page above, please summarize the key points.
```

## Tips

1. Use `--show` to preview content before adding it to your conversation:
   ```python
   %confluence SPACE:PageTitle --show
   ```

2. When searching with CQL, keep queries specific to avoid retrieving too much content:
   ```python
   %confluence --cql "space = DOCS AND title ~ 'API Reference'" --max 3
   ```

3. For large pages, consider adding them as system messages to help the LLM understand the context:
   ```python
   %confluence SPACE:PageTitle --system
   ```

4. For better rendering of complex pages, use the default Markdown format. Only use `--text` if you need plain text:
   ```python
   # Default is already Markdown (recommended for most uses)
   %confluence SPACE:PageTitle
   
   # Use text only if needed for specific use cases
   %confluence SPACE:PageTitle --text
   ```

5. For searches where you just want to find relevant pages before deciding which to fetch:
   ```python
   %confluence --cql "space = DOCS AND created > '2024/01/01'" --no-content
   ```

## Examples

### Basic Usage

```python-repl
# Fetch a specific page (already in Markdown format by default)
%confluence DOCS:Project Overview

# Ask LLM about it
%%llm
Based on the Project Overview page, what are the key milestones?
```

### Search Then Fetch

```python
# First search for relevant pages without content
%confluence --cql "space = DOCS AND title ~ 'API'" --no-content --show

# Then fetch the specific page you're interested in
%confluence DOCS:API Reference
```

### Combining with Other Features

```python-repl
# Fetch project requirements from Confluence
%confluence PROJ:Requirements --system

# Fetch a specific Jira ticket
%jira PROJECT-123

# Ask LLM to analyze both
%%llm
Given the project requirements from Confluence and the Jira ticket above, 
what should be our implementation approach?
```