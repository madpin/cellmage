# 📝 CellMage Magic Command Cheatsheet

This cheatsheet provides a comprehensive reference for all CellMage magic commands and their arguments.

## Core Magic Commands

### 1. `%llm_config` - Configuration Magic

```python
%llm_config [options]
```

| Argument | Description |
|----------|-------------|
| `-p`, `--persona` *NAME* | Select and activate a persona by name |
| `--show-persona` | Show the currently active persona details |
| `--list-personas` | List available persona names |
| `--list-mappings` | List current model name mappings |
| `--add-mapping` *ALIAS* *FULL_NAME* | Add a model name mapping (e.g., `--add-mapping g4 gpt-4`) |
| `--remove-mapping` *ALIAS* | Remove a model name mapping |
| `--set-override` *KEY* *VALUE* | Set a temporary LLM param override (e.g., `--set-override temperature 0.5`) |
| `--remove-override` *KEY* | Remove a specific override key |
| `--clear-overrides` | Clear all temporary LLM param overrides |
| `--show-overrides` | Show the currently active overrides |
| `--clear-history` | Clear the current chat history (keeps system prompt) |
| `--show-history` | Display the current message history |
| `--save` [*FILENAME*] | Save session. If no name, uses current session ID. '.md' added automatically |
| `--load` *SESSION_ID* | Load session from specified identifier (filename without .md) |
| `--list-sessions` | List saved session identifiers |
| `--auto-save` | Enable automatic saving of conversations to the conversations directory |
| `--no-auto-save` | Disable automatic saving of conversations |
| `--list-snippets` | List available snippet names |
| `--snippet` *NAME* | Add user snippet content before sending prompt (can be used multiple times) |
| `--sys-snippet` *NAME* | Add system snippet content before sending prompt (can be used multiple times) |
| `--status` | Show current status (persona, overrides, history length) |
| `--model` *NAME* | Set the default model for the LLM client |
| `--adapter` {direct,langchain} | Switch to a different LLM adapter implementation |

### 2. `%%llm` - LLM Cell Magic

```python
%%llm [options]
Your prompt to the LLM goes here...
```

| Argument | Description |
|----------|-------------|
| `-p`, `--persona` *NAME* | Use specific persona for THIS call only |
| `-m`, `--model` *NAME* | Use specific model for THIS call only |
| `-t`, `--temperature` *VALUE* | Set temperature for THIS call |
| `--max-tokens` *NUMBER* | Set max_tokens for THIS call |
| `--no-history` | Do not add this exchange to history |
| `--no-stream` | Do not stream output (wait for full response) |
| `--no-rollback` | Disable auto-rollback check for this cell run |
| `--param` *KEY* *VALUE* | Set any other LLM param ad-hoc (e.g., `--param top_p 0.9`). Can be used multiple times |
| `--list-snippets` | List available snippet names |
| `--snippet` *NAME* | Add user snippet content before sending prompt (can be used multiple times) |
| `--sys-snippet` *NAME* | Add system snippet content before sending prompt (can be used multiple times) |

### 3. `%llm_config_persistent` - Ambient Mode Magic

```python
%llm_config_persistent [options]
```

Accepts the same arguments as `%llm_config` but also enables ambient mode (all regular cells are processed as LLM prompts).

### 4. `%disable_llm_config_persistent` - Disable Ambient Mode

```python
%disable_llm_config_persistent
```

Disables ambient mode, returning the notebook to normal operation.

### 5. `%%py` - Execute Python in Ambient Mode

```python
%%py
# Python code to run
print("Hello World")
```

When ambient mode is active, this magic command lets you execute a specific cell as Python code.

## Integration Magic Commands

### 1. `%confluence` - Confluence Wiki Integration

```python
%confluence [identifier] [options]
```

| Argument | Description |
|----------|-------------|
| `identifier` | Page identifier (SPACE:Title format or page ID) |
| `--cql` *QUERY* | Confluence Query Language (CQL) search query |
| `--max` *NUMBER* | Maximum number of results for CQL queries (default: 5) |
| `--system` | Add content as a system message (rather than user) |
| `--show` | Display the content without adding to history |
| `--text` | Use plain text format instead of Markdown (Markdown is default) |
| `--no-content` | For CQL search, return only metadata without page content |
| `--content` | For CQL search, fetch full content of each page (makes additional API calls) |

### 2. `%jira` - Jira Integration

```python
%jira [issue_key] [options]
```

| Argument | Description |
|----------|-------------|
| `issue_key` | Jira issue key (e.g., PROJECT-123) |
| `--jql` *QUERY* | JQL search query instead of a specific issue |
| `--max` *NUMBER* | Maximum number of results for JQL search (default: 5) |
| `--fields` *FIELDS* | Comma-separated list of fields to include |
| `--comments` | Include issue comments |
| `--system` | Add as system message instead of user message |
| `--show` | Display content without adding to history |
| `--text` | Use plain text instead of Markdown format |

### 3. `%github` - GitHub Integration

```python
%github [repo/path] [options]
```

| Argument | Description |
|----------|-------------|
| `repo_path` | Repository owner/name or file path within a repository |
| `--issue` *NUMBER* | Fetch a specific issue by number |
| `--pr` *NUMBER* | Fetch a specific pull request by number |
| `--search` *QUERY* | Search for issues with the given query |
| `--max` *NUMBER* | Maximum number of search results (default: 5) |
| `--comments` | Include comments on issues/PRs |
| `--system` | Add as system message instead of user message |
| `--show` | Display content without adding to history |
| `--branch` *NAME* | Branch to use when fetching files (default: main/master) |

### 4. `%gitlab` - GitLab Integration

```python
%gitlab [repo/path] [options]
```

| Argument | Description |
|----------|-------------|
| `repo_path` | Project path or file path within a project |
| `--issue` *NUMBER* | Fetch a specific issue by number |
| `--mr` *NUMBER* | Fetch a specific merge request by number |
| `--search` *QUERY* | Search for issues with the given query |
| `--max` *NUMBER* | Maximum number of search results (default: 5) |
| `--comments` | Include comments on issues/MRs |
| `--system` | Add as system message instead of user message |
| `--show` | Display content without adding to history |
| `--branch` *NAME* | Branch to use when fetching files (default: main/master) |

### 5. `%webcontent` - Web Content Integration

```python
%webcontent [url] [options]
```

| Argument | Description |
|----------|-------------|
| `url` | URL of the webpage to fetch |
| `--clean` | Clean and extract main content (default behavior) |
| `--raw` | Get raw HTML content without cleaning |
| `--method` *METHOD* | Content extraction method: trafilatura (default), bs4, or simple |
| `--system` | Add as system message instead of user message |
| `--show` | Display content without adding to history |
| `--include-images` | Include image references in the output |
| `--no-links` | Remove hyperlinks from the output |
| `--timeout` *SECONDS* | Request timeout in seconds (default: 30) |

### 6. `%gdocs` - Google Docs Integration

```python
%gdocs [document_id] [options]
```

| Argument | Description |
|----------|-------------|
| `document_id` | Google Document ID |
| `--system` | Add as system message instead of user message |
| `--show` | Display content without adding to history |
| `--search` *QUERY* | Search for Google Docs files containing the specified term |
| `--content` | Retrieve and display content for search results |
| `--max-results` *NUMBER* | Maximum number of search results to return (default: 10) |
| `--max-content` *NUMBER* | Maximum number of documents to retrieve content for (default: 3) |
| `--timeout` *SECONDS* | Request timeout in seconds (default: 300) |
| `--author` *EMAIL* | Filter documents by author/owner email (comma-separated for multiple) |
| `--modified-after`, `--updated` *DATE* | Filter by modification date (YYYY-MM-DD or natural language) |
| `--order-by` *FIELD* | How to order search results (relevance, modifiedTime, createdTime, name) |
| `--auth-type` *TYPE* | Authentication type to use (oauth or service_account) |

### 7. `%sqlite` - SQLite Storage Management

```python
%sqlite [options]
```

| Argument | Description |
|----------|-------------|
| `--status` | Show the current state of the SQLite storage |
| `--stats` | Display statistics about stored conversations |
| `--list` | List all stored conversations |
| `--new` | Start a new conversation |
| `--load` *ID* | Load a specific conversation by ID |
| `--delete` *ID* | Delete a conversation by ID |
| `--tag` *ID* *TAG* | Add a tag to a conversation |
| `--search` *QUERY* | Search for conversations with content matching the query |
| `--export` *PATH* | Export a conversation to markdown file |
| `--import-md` *PATH* | Import a conversation from markdown file |

## Example Usage

### Core Commands

```python
# Load the extension
%load_ext cellmage.integrations.ipython_magic

# Set the default model and persona
%llm_config --model gpt-4o --persona python_expert

# Ask a question with a specific model for this call only
%%llm -m gpt-4o
Explain the visitor pattern in software design

# Enable ambient mode with specific settings
%llm_config_persistent --model gpt-4o-mini --temperature 0.7

# Execute Python code in ambient mode
%%py
import pandas as pd
print(pd.__version__)

# Disable ambient mode
%disable_llm_config_persistent
```

### Integration Commands

```python
# Load Confluence extension
%load_ext cellmage.integrations.confluence_magic

# Fetch a Confluence page
%confluence TEAM:Project Overview

# Search Confluence
%confluence --cql "space = DEV AND title ~ 'Architecture'"

# Load GitHub extension
%load_ext cellmage.integrations.github_magic

# Get a specific GitHub issue
%github myorg/myrepo --issue 42

# Get web content
%load_ext cellmage.integrations.webcontent_magic
%webcontent https://example.com/article
```
