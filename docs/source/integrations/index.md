# 🔌 Integrations

CellMage's power extends beyond just LLM interactions. It seamlessly integrates with your existing tools and services, bringing their context directly into your notebooks.

## Available Integrations

```{toctree}
:maxdepth: 1

../jira_integration
../confluence_integration
../github_integration
../gitlab_integration
../webcontent_integration
../gdocs_integration
../image_integration
image_magic_integration
```

## Integration Features

Each integration brings unique capabilities to your magical workflow:

### Jira Integration

Fetch ticket information, create comments, update statuses, and more without leaving your notebook.

```ipython
%jira PROJ-123  # Get ticket details
```

### Confluence Integration

Import knowledge from your company wiki directly into your LLM context.

```ipython
%confluence "Page Title"  # Import page content
```

### GitHub Integration

Access repository information, pull requests, issues, and more.

```ipython
%github repo:user/repo issue:42  # Get issue details
```

### GitLab Integration

Similar to GitHub, but for GitLab repositories and merge requests.

```ipython
%gitlab project:group/project mr:15  # Get merge request details
```

### WebContent Integration

Fetch, clean, and extract content from websites to use as context for your prompts.

```ipython
%webcontent https://example.com  # Extract and import website content
```

### Google Docs Integration

Import content from Google Documents directly into your LLM context.

```ipython
%gdocs https://docs.google.com/document/d/YOUR_DOC_ID/edit  # Import document content
```

### Image Integration

Process, display, and add images to your LLM conversations and context.

```ipython
%img path/to/image.jpg --resize 800 --show  # Process, display, and add to LLM context
```

## Adding Your Own Integrations

CellMage is designed to be extensible. You can create your own integrations by:

1. Subclassing `BaseMagic` from `cellmage.integrations.base_magic`
2. Implementing the required methods
3. Registering your magic with the IPython kernel

See the [Developer Guide](../developer/index.md) for more details on creating custom integrations.
