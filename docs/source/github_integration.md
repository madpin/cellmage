# GitHub Integration

CellMage provides integration with GitHub through the `%github` magic command, allowing you to fetch GitHub repositories and pull requests directly into your notebook and use them as context for LLM queries.

## Installation

To use the GitHub integration, install CellMage with the GitHub extra dependency:

```bash
pip install "cellmage[github]"
```

This will install the required dependencies including `PyGithub` and `python-dotenv`.

## Configuration

The GitHub integration requires a GitHub personal access token. You can set it using environment variables:

```bash
# In your terminal
export GITHUB_TOKEN="your_personal_access_token"

# Or in a .env file
GITHUB_TOKEN=your_personal_access_token
```

To create a GitHub Personal Access Token:
- Go to your GitHub account settings → Developer settings → Personal access tokens
- Generate a new token with the `repo` scope (for private repositories) or just `public_repo` for public repositories
- Copy the token and set it as your `GITHUB_TOKEN` environment variable

## Basic Usage

To fetch a specific repository:

```ipython
%github username/repo
```

This fetches the repository summary and adds it as a user message in the chat history.

## Advanced Usage

### Fetching Pull Requests

You can also fetch a specific pull request from a repository:

```ipython
%github username/repo --pr 123
```

### Command Options

- `--pr ID`: Fetch a specific pull request by ID
- `--system`: Add content as system message instead of user message
- `--show`: Only display the content without adding it to the chat history
- `--clean`: Clean the repository content to focus on code (removes non-essential files)
- `--full-code`: Include all code content from the repository (may be very large)
- `--exclude-dir PATTERN`: Exclude directories matching the pattern (can use multiple times)
- `--exclude-file PATTERN`: Exclude files matching the pattern (can use multiple times)
- `--exclude-ext EXT`: Exclude files with the specified extension (can use multiple times)
- `--exclude-regex PATTERN`: Exclude files matching the regex pattern (can use multiple times)
- `--contributors-months N`: Include contributors from the last N months (default: 6)

### Examples

Fetch a repository and add it to history:
```ipython
%github username/repo
```

Fetch a repository and add it as system context:
```ipython
%github username/repo --system
```

Just view a repository summary without adding to history:
```ipython
%github username/repo --show
```

Fetch a pull request:
```ipython
%github username/repo --pr 123
```

View a pull request without adding to history:
```ipython
%github username/repo --pr 123 --show
```

Exclude certain directories and file types:
```ipython
%github username/repo --exclude-dir "node_modules" --exclude-ext ".json" --exclude-ext ".md"
```

## Using GitHub Content with LLM Queries

Once you've fetched GitHub content, you can reference it in your LLM queries:

```ipython
# First, fetch the repository
%github username/repo

# Then, reference it in your prompt
%%llm
Based on the GitHub repository above, can you explain the project architecture and suggest improvements?
```

Or with pull requests:

```ipython
# First, fetch the pull request
%github username/repo --pr 123

# Then, use it as context in your prompt
%%llm
Please review the pull request above and suggest any improvements or issues to address.
```

## Troubleshooting

### Authentication Issues

1. **Verify your token is set properly**:
   ```ipython
   import os
   print("GITHUB_TOKEN is set:", os.environ.get("GITHUB_TOKEN") is not None)
   ```

2. **Check token scope and permissions**:
   - Ensure your token has the required scopes (`repo` for private repositories, `public_repo` for public ones)
   - Verify the token hasn't expired
   - Regenerate the token if necessary

### Rate Limiting

GitHub has API rate limits that may affect your usage:

1. **Authenticated rate limits**: With a token, you get 5,000 requests per hour
2. **Unauthenticated rate limits**: Without a token, only 60 requests per hour
3. **Rate limit errors**: If you see `403 Rate Limit Exceeded` errors, wait for your rate limit to reset

### Repository Access Issues

1. **Private repositories**: Ensure your token has `repo` scope for accessing private repositories
2. **Organization repositories**: You need appropriate organization permissions if accessing org repositories
3. **Repository not found**: Check if the repository exists and you've spelled the name correctly

### Large Repository Problems

1. **Timeout errors**: For very large repositories, you might experience timeouts
2. **Memory issues**: Large repositories may cause memory problems
3. **Solutions**:
   - Use `--clean` to reduce the amount of data
   - Use `--exclude-dir`, `--exclude-file`, and `--exclude-ext` to filter content
   - Avoid `--full-code` for large repositories

For any persistent issues, you can enable debug logging:

```python
import logging
from cellmage.utils.logging import setup_logging
setup_logging(level=logging.DEBUG)
# The logs will be written to cellmage.log in your working directory
```
