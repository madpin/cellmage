# Cellmage Development Setup

This document provides instructions for setting up a development environment for CellMage.

## Using the Virtual Environment

The project uses a Python virtual environment (`.venv`) to manage dependencies.

### Initial Setup

```bash
# Create the virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.\.venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .

# Install testing dependencies
pip install pytest pytest-cov
```

### Running Tests

With the virtual environment activated:

```bash
# Run all tests
pytest

# Run integration tests
pytest tests/integration -v

# Run a specific test file
pytest tests/integration/test_github_magic.py -v
```

### VS Code Integration

The project includes settings for VS Code that configure it to use the virtual environment:

1. Open the folder in VS Code
2. Ensure you have the Python extension installed
3. VS Code should automatically detect and use the `.venv` virtual environment
4. Use the Test Explorer to run tests, or use the Terminal within VS Code

## Environment Variables

Create a `.env` file in the project root with any necessary environment variables for development:

```
OPENAI_API_KEY=your_api_key
GITHUB_PAT=your_github_token
# Add other API keys as needed
```

## Pre-commit Hooks

See `PRE_COMMIT.md` for information on setting up pre-commit hooks.
