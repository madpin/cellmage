#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
# set -u # Optional: uncomment if you want stricter variable checking
# Ensure pipeline failures are reported
set -o pipefail

echo "🚀 Starting project setup for Notebook LLM (cellmage)..."

# --- Create Root Level Directories ---
echo "Creating root directories..."
mkdir -p llm_personas
mkdir -p llm_conversations
mkdir -p snippets
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p cellmage # Create the main project folder

# --- Create Source Directories inside 'cellmage' ---
echo "Creating source directories inside 'cellmage/src/notebook_llm'..."
SRC_BASE="cellmage/src/notebook_llm"
mkdir -p "${SRC_BASE}"
mkdir -p "${SRC_BASE}/resources"
mkdir -p "${SRC_BASE}/storage"
mkdir -p "${SRC_BASE}/adapters"
mkdir -p "${SRC_BASE}/integrations"
mkdir -p "${SRC_BASE}/utils"

# --- Create Empty Python Files ---
echo "Creating Python files..."
touch "${SRC_BASE}/__init__.py"
touch "${SRC_BASE}/config.py"
touch "${SRC_BASE}/models.py"
touch "${SRC_BASE}/exceptions.py"
touch "${SRC_BASE}/interfaces.py"
touch "${SRC_BASE}/chat_manager.py"
touch "${SRC_BASE}/history_manager.py"

touch "${SRC_BASE}/resources/__init__.py"
touch "${SRC_BASE}/resources/file_loader.py"
touch "${SRC_BASE}/resources/memory_loader.py" # Optional example

touch "${SRC_BASE}/storage/__init__.py"
touch "${SRC_BASE}/storage/markdown_store.py"
touch "${SRC_BASE}/storage/memory_store.py"   # Optional example

touch "${SRC_BASE}/adapters/__init__.py"
touch "${SRC_BASE}/adapters/llm_client.py"

touch "${SRC_BASE}/integrations/__init__.py"
touch "${SRC_BASE}/integrations/ipython_magic.py"

touch "${SRC_BASE}/utils/__init__.py"
touch "${SRC_BASE}/utils/logging.py"

# --- Create Test Files ---
echo "Creating test files..."
touch tests/conftest.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
# Add specific test files if known, e.g.:
touch tests/unit/test_history_manager.py
touch tests/unit/test_chat_manager_core.py
touch tests/integration/test_ipython_magic.py
touch tests/integration/test_file_resources.py

# --- Create Example/Config Files ---
echo "Creating example/config files..."
touch llm_personas/example_persona.md
touch llm_conversations/.gitkeep # Keep directory in git even if empty initially
touch snippets/example_snippet.md
touch README.md
touch .env.example
touch pyproject.toml

# --- Add Basic Content to Key Files ---
echo "Adding basic content to key files..."

# README.md
cat << EOF > README.md
# Notebook LLM (cellmage)

Project to facilitate LLM interactions within notebooks.

## Setup

1.  Install dependencies: \`poetry install\`
2.  Configure environment variables (copy \`.env.example\` to \`.env\` and fill values).
3.  Place persona files in \`llm_personas/\`.

## Usage

(Add basic usage instructions here)
EOF

# .env.example
cat << EOF > .env.example
# Environment variables for NotebookLLM (cellmage)
# Copy this file to .env and fill in your values

# Required for most LLM interactions
NBLLM_API_KEY=YOUR_LLM_API_KEY
NBLLM_API_BASE=YOUR_LLM_API_BASE_URL # e.g., https://api.openai.com/v1

# Optional Settings (Defaults shown)
# NBLLM_LOG_LEVEL=INFO
# NBLLM_PERSONAS_DIR=llm_personas
# NBLLM_SAVE_DIR=llm_conversations
# NBLLM_SNIPPETS_DIR=snippets
# NBLLM_DEFAULT_MODEL= # e.g., gpt-4o
EOF

# pyproject.toml (Basic Poetry setup)
cat << EOF > pyproject.toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "cellmage" # Project name based on folder
version = "0.1.0"
description = "Notebook LLM Interaction Tool"
authors = ["Your Name <you@example.com>"] # CHANGE THIS
readme = "README.md"
packages = [{include = "notebook_llm", from = "cellmage/src"}]
license = "MIT" # CHOOSE A LICENSE

[tool.poetry.dependencies]
python = "^3.10"
litellm = "^1.30" # Specify a recent compatible version
pyyaml = "^6.0"
pydantic = "^2.5"
pydantic-settings = "^2.1"
# Optional dependencies below - install via extras
ipython = {version = "^8.0", optional = true}
pandas = {version = "^2.0", optional = true}
requests = {version = "^2.30", optional = true}
langchain-core = {version = "^0.1", optional = true}

[tool.poetry.extras]
ipython = ["ipython"]
pandas = ["pandas"]
requests = ["requests"]
langchain = ["langchain-core"]
all = ["ipython", "pandas", "requests", "langchain-core"]

[tool.poetry.group.dev.dependencies]
pytest = "^7.4"
pytest-asyncio = "^0.21" # For testing async code
ruff = "^0.1" # Linter/formatter
mypy = "^1.7" # Static type checker

[tool.pytest.ini_options]
pythonpath = ["cellmage/src"] # Make src importable for tests
testpaths = ["tests"]
asyncio_mode = "auto" # For pytest-asyncio

[tool.ruff]
line-length = 88
select = ["E", "W", "F", "I", "UP", "B", "C4", "ASYNC", "TCH"] # Select rules (example set)
ignore = ["E501"] # Ignore line length errors if needed selectively

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true # Start with this, reduce later if possible
# Add namespace_packages = true if needed
# Add plugins if using pydantic mypy plugin etc.

EOF

# Minimal content for example files
echo "# Example Persona" > llm_personas/example_persona.md
echo "---" >> llm_personas/example_persona.md
echo "model: your-default-model-here" >> llm_personas/example_persona.md
echo "temperature: 0.7" >> llm_personas/example_persona.md
echo "---" >> llm_personas/example_persona.md
echo "" >> llm_personas/example_persona.md
echo "You are a helpful assistant." >> llm_personas/example_persona.md

echo "This is an example snippet." > snippets/example_snippet.md

# Add basic version/init to main __init__.py
echo "__version__ = '0.1.0'" > "${SRC_BASE}/__init__.py"
echo "" >> "${SRC_BASE}/__init__.py"
echo "# Expose key classes for easier import" >> "${SRC_BASE}/__init__.py"
echo "from .chat_manager import ChatManager" >> "${SRC_BASE}/__init__.py"
echo "from .exceptions import NotebookLLMError, ResourceNotFoundError" >> "${SRC_BASE}/__init__.py"
# Add others as needed

echo "✅ Project structure created successfully!"
echo "➡️ Next steps:"
echo "   1. Review 'pyproject.toml' and update author details, license, etc."
echo "   2. Copy '.env.example' to '.env' and add your API keys/endpoints."
echo "   3. Install dependencies: poetry install --all-extras"
echo "   4. Start implementing the classes!"

exit 0