# 🧙‍♂️ Developer Guide

Welcome to the CellMage developer guide! This section is dedicated to those who want to understand CellMage's inner workings, contribute to the project, or extend its functionality.

## 🏗️ Architecture Overview

CellMage is built with a modular architecture designed for flexibility and extensibility:

```
+------------------+      +-------------------+      +---------------+
|                  |      |                   |      |               |
|  Magic Commands  +----->+  Chat Manager     +----->+  LLM Adapters |
|                  |      |                   |      |               |
+------------------+      +-------------------+      +---------------+
        ^                         |                         |
        |                         v                         v
+------------------+      +-------------------+      +---------------+
|                  |      |                   |      |               |
|  Integrations    |      |  Conversation     |      |  API Services |
|                  |      |  Manager          |      |               |
+------------------+      +-------------------+      +---------------+
        ^                         |
        |                         v
+------------------+      +-------------------+
|                  |      |                   |
|  Resources       |      |  Storage          |
|  (Personas,      |      |  (SQLite,         |
|   Snippets)      |      |   Markdown)       |
+------------------+      +-------------------+
```

Key components:
- **Magic Commands**: Entry point for user interactions via IPython
- **Chat Manager**: Orchestrates conversations with LLMs
- **Adapters**: Interface with different LLM providers
- **Conversation Manager**: Tracks and manages conversation history
- **Storage**: Persists conversations to disk
- **Integrations**: Connects with external services
- **Resources**: Manages personas and snippets


## 🧱 Core Classes

| Class | Purpose |
|-------|---------|
| `ChatManager` | Central orchestrator for LLM interactions |
| `ConversationManager` | Manages conversation history and state |
| `BaseMagic` | Base class for all magic commands |
| `DirectClient` | Adapter for direct API calls |
| `LangchainClient` | Adapter for Langchain integration |
| `SQLiteStore` | Storage implementation using SQLite |
| `MarkdownStore` | Storage implementation using Markdown files |

## 🛠️ Development Setup

### Prerequisites

- Python 3.9+
- [Poetry](https://python-poetry.org/) (recommended for dependency management)
- Access to an OpenAI API key or compatible service

### Setting Up Your Environment

```bash
# Clone the repository
git clone https://github.com/madpin/cellmage.git
cd cellmage

# Install dependencies
pip install -e .
pip install -r requirements-docs.txt  # For documentation development
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit
pytest tests/integration

# Run magic commands tests specifically
python tests/run_magic_tests.py
```

For more details on testing magic commands, see [Magic Commands Testing](magic_commands_testing.md).

### Building Documentation

```bash
cd docs
make html
```

The documentation will be built in `docs/build/html`.

## 🔄 Contribution Workflow

1. **Setup**: Fork the repository and create a branch
2. **Develop**: Make your changes, adding tests as needed
3. **Test**: Ensure all tests pass
4. **Document**: Update or add documentation as needed
5. **Submit**: Create a pull request with a clear description
6. **Review**: Address any feedback from maintainers

See our [Contributing Guide](../CONTRIBUTING.md) for more details.

## 🔌 Creating Custom Extensions

### Custom Magic Commands

To create a new magic command:

1. Subclass `BaseMagic` from `cellmage.integrations.base_magic`
2. Implement the required methods:
   ```ipython
   class CustomMagic(BaseMagic):
       name = "custom"

       def line_magic(self, line):
           # Implementation for %custom
           pass

       def cell_magic(self, line, cell):
           # Implementation for %%custom
           pass
   ```
3. Register your magic with IPython:
   ```ipython
   def load_ipython_extension(ipython):
       custom_magic = CustomMagic(ipython)
       ipython.register_magics(custom_magic)
   ```

### Custom Adapters

To add support for a new LLM provider:

1. Subclass `interfaces.LLMAdapter`
2. Implement the required methods:
   ```ipython
   class CustomAdapter(LLMAdapter):
       def send_message(self, messages, **kwargs):
           # Implementation to send messages to the custom LLM
           pass

       def get_completion(self, prompt, **kwargs):
           # Implementation for simple completions
           pass
   ```

### Custom Storage Backends

To create a new storage backend:

1. Subclass `interfaces.ConversationStore`
2. Implement the required methods for saving and loading conversations

## 📊 Performance Optimization

When working with CellMage, keep these performance considerations in mind:

1. **Token Usage**: Monitor and optimize token usage in prompts
2. **Streaming**: Use streaming for better user experience with larger responses
3. **Storage**: SQLite is more efficient than Markdown for frequent operations
4. **Memory Management**: Release resources when no longer needed

## 🔍 Debugging

Enable debug mode to see detailed logs:

```ipython
from cellmage.utils.logging import setup_logging
import logging
setup_logging(level=logging.DEBUG)
```

Logs will be written to `cellmage.log` in your working directory.

## 📝 Release Process

Our release process follows these steps:

1. Update version in `cellmage/version.py`
2. Update changelog
3. Create a release branch
4. Run tests and build documentation
5. Tag the release
6. Publish to PyPI

For detailed instructions, see [Release Process](https://github.com/madpin/cellmage/blob/main/RELEASE_PROCESS.md).

## 🔗 Useful Resources

- [Project Board](https://github.com/madpin/cellmage/projects)
- [Issue Tracker](https://github.com/madpin/cellmage/issues)
- [Discussion Forum](https://github.com/madpin/cellmage/discussions)

```{toctree}
:maxdepth: 2
:caption: Developer Guides

documentation_guide
```
