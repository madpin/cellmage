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

1. **Environment Variables**: Set the following variables in your environment or in a `.env` file:
   ```
   GITHUB_TOKEN=your_personal_access_token
   ```

2. To create a GitHub Personal Access Token:
   - Go to your GitHub account settings → Developer settings → Personal access tokens
   - Generate a new token with the `repo` scope (for private repositories) or just `public_repo` for public repositories
   - Copy the token and set it as your `GITHUB_TOKEN` environment variable

## Using the `%github` Magic Command

### Basic Usage

To fetch a specific repository:

```python
%github username/repo
```

This fetches the repository summary and adds it as a user message in the chat history.

### Fetching Pull Requests

You can also fetch a specific pull request from a repository:

```python
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
```python
%github username/repo
```

Fetch a repository and add it as system context:
```python
%github username/repo --system
```

Just view a repository summary without adding to history:
```python
%github username/repo --show
```

Fetch a pull request:
```python
%github username/repo --pr 123
```

View a pull request without adding to history:
```python
%github username/repo --pr 123 --show
```

Exclude certain directories and file types:
```python
%github username/repo --exclude-dir "node_modules" --exclude-ext ".json" --exclude-ext ".md"
```

## Using GitHub Content with LLM Queries

Once you've fetched GitHub content, you can reference it in your LLM queries:

```text
# First, fetch the repository
%github username/repo

# Then, reference it in your prompt
%%llm
Based on the GitHub repository above, can you explain the project architecture and suggest improvements?
```

Or with pull requests:

```text
# First, fetch the pull request
%github username/repo --pr 123

# Then, use it as context in your prompt
%%llm
Please review the pull request above and suggest any improvements or issues to address.
```