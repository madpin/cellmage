# GitLab Integration

CellMage provides integration with GitLab through the `%gitlab` magic command, allowing you to fetch GitLab repositories and merge requests directly into your notebook and use them as context for LLM queries.

## Installation

To use the GitLab integration, install CellMage with the `gitlab` extra:

```bash
pip install cellmage[gitlab]
```

## Configuration

The GitLab integration requires the following environment variables:

- `GITLAB_URL`: The URL of your GitLab instance (e.g., `https://gitlab.com` for public GitLab)
- `GITLAB_PAT` or `GITLAB_PRIVATE_TOKEN`: Your GitLab Personal Access Token

You can set these in a `.env` file in your working directory or directly in your environment.

## Using the `%gitlab` Magic Command

### Basic Usage

To fetch a specific repository:

```python
%gitlab namespace/project
```

This fetches the repository summary and adds it as a user message in the chat history.

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
```

Then in a new cell, you can ask the LLM about it:

```
%%llm
Given the GitLab repository above, can you explain the architecture of this codebase?
```

Or with a merge request:

```python
# First, fetch a merge request
%gitlab namespace/project --mr 123
```

```
%%llm
Please review the merge request above and identify any potential issues or improvements.
```

This integration makes it easy to use your GitLab repositories and merge requests as context for your LLM queries, enhancing your ability to work with and understand project-specific code.