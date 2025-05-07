# GitLab Integration

CellMage provides integration with GitLab through the `%gitlab` magic command, allowing you to fetch GitLab repositories and merge requests directly into your notebook and use them as context for LLM queries.

## Installation

To use the GitLab integration, install CellMage with the `gitlab` extra:

```bash
pip install "cellmage[gitlab]"
```

## Configuration

The GitLab integration requires the following environment variables:

- `GITLAB_URL`: The URL of your GitLab instance (e.g., `https://gitlab.com` for public GitLab)
- `GITLAB_PAT` or `GITLAB_PRIVATE_TOKEN`: Your GitLab Personal Access Token

You can set these in a `.env` file in your working directory or directly in your environment:

```bash
# In your terminal
export GITLAB_URL="https://gitlab.com"
export GITLAB_PAT="your_gitlab_personal_access_token"

# Or in a .env file
GITLAB_URL=https://gitlab.com
GITLAB_PAT=your_gitlab_personal_access_token
```

To create a GitLab Personal Access Token:
- Go to your GitLab account → Preferences → Access Tokens
- Create a token with the `api` scope for full API access, or `read_api` for read-only access
- Copy the token and set it as your `GITLAB_PAT` environment variable

## Basic Usage

To fetch a specific repository:

```python
%gitlab namespace/project
```

This fetches the repository summary and adds it as a user message in the chat history.

## Advanced Usage

### Fetching Merge Requests

You can also fetch a specific merge request from a repository:

```python
%gitlab namespace/project --mr 123
```

### Command Options

- `--mr ID`: Fetch a specific merge request by ID
- `--system`: Add content as system message instead of user message
- `--show`: Only display the content without adding it to the chat history
- `--clean`: Clean the repository content to focus on code (removes non-essential files)

### Examples

Fetch a repository and add it to history:
```python
%gitlab namespace/project
```

Fetch a repository and add it as system context:
```python
%gitlab namespace/project --system
```

Just view a repository summary without adding to history:
```python
%gitlab namespace/project --show
```

Fetch a merge request:
```python
%gitlab namespace/project --mr 123
```

View a merge request without adding to history:
```python
%gitlab namespace/project --mr 123 --show
```

## Using GitLab Content with LLM Queries

After loading GitLab content with `%gitlab`, you can refer to it in your LLM prompts:

```python
# First, fetch a repository
%gitlab namespace/project

# Then ask the LLM about it
%%llm
Given the GitLab repository above, can you explain the architecture of this codebase?
```

Or with a merge request:

```python
# First, fetch a merge request
%gitlab namespace/project --mr 123

# Then ask the LLM about it
%%llm
Please review the merge request above and identify any potential issues or improvements.
```

This integration makes it easy to use your GitLab repositories and merge requests as context for your LLM queries, enhancing your ability to work with and understand project-specific code.

## Troubleshooting

### Authentication Issues

1. **Verify your environment variables**:
   ```python
   import os
   print("GITLAB_URL:", os.environ.get("GITLAB_URL"))
   print("GITLAB_PAT is set:", os.environ.get("GITLAB_PAT") is not None)
   print("GITLAB_PRIVATE_TOKEN is set:", os.environ.get("GITLAB_PRIVATE_TOKEN") is not None)
   ```

2. **Check token validity**:
   - Ensure your token has not expired
   - Verify the token has sufficient scope (`api` or `read_api`)
   - Regenerate your token if necessary

3. **URL format**:
   - Ensure your GitLab URL is formatted correctly (includes `https://`)
   - For self-hosted instances, check that the URL is accessible from your environment

### Access Permission Issues

1. **Project visibility**: Make sure the project is public or your account has proper access
2. **Group/namespace access**: Check that you have access to the parent group
3. **Token permissions**: Verify the token has permissions for the project

### Connection Problems

1. **Self-hosted instance issues**:
   - Check the network connection to your self-hosted GitLab instance
   - Verify the instance is running and accessible
   - Check for any SSL certificate issues

2. **Rate limiting**:
   - GitLab enforces API rate limits that may affect your usage
   - If you receive rate limit errors, wait and try again later

### Project Not Found Issues

1. **Check namespace/project path**:
   - Ensure you're using the full path (e.g., `group/subgroup/project`)
   - The path is case-sensitive, so verify the exact spelling
   - Check if the project still exists or has been renamed

For persistent issues, enable debug logging:

```python
import logging
from cellmage.utils.logging import setup_logging
setup_logging(level=logging.DEBUG)
# The logs will be written to cellmage.log in your working directory
```
