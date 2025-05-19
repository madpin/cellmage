# 🪄 Cellmage: Your Notebook LLM Wizard 🎩

**Tired of wrestling with LLM APIs in your notebooks? Cellmage seamlessly integrates Large Language Models (LLMs) directly into your Jupyter/IPython workflow.**

Stop copy-pasting, managing complex client code, or losing context. Cellmage provides intuitive magic commands (`%%llm`, `%llm_config`) to chat with models, manage conversation history, switch personas, inject context snippets, and even enable an "ambient" mode where *every* cell becomes an LLM prompt!

It's designed for **data scientists, software engineers, researchers, and students** who want to leverage LLMs *within* their existing notebook environment with minimal friction. Spend less time on boilerplate, more time on solving actual problems (or generating cool sci-fi plots, we don't judge!).

[![Github version](https://img.shields.io/github/v/release/madpin/cellmage)](https://img.shields.io/github/v/release/madpin/cellmage)
[![PyPI version](https://badge.fury.io/py/cellmage.svg)](https://badge.fury.io/py/cellmage)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation Status](https://readthedocs.org/projects/cellmage/badge/?version=latest)](https://cellmage.readthedocs.io/en/latest/?badge=latest)
[![Download Status](https://img.shields.io/pypi/dd/cellmage)](https://img.shields.io/pypi/dd/cellmage)

---

## ✨ Key Features

*   **🧙 IPython Magic Commands:** Effortlessly interact with LLMs using simple `%` and `%%` commands.
*   **🎭 Personas:** Define and switch between different AI personalities (e.g., 'code_reviewer', 'data_analyst', 'rubber_duck_debugger').
*   **🔮 Ambient Mode:** Optionally turn your entire notebook into an LLM chat interface.
*   **✂️ Snippets:** Inject reusable code or text snippets into your prompts on the fly.
*   **💾 History & Session Management:** Automatically track conversations, save/load sessions to Markdown, and manage context.
*   **⚙️ Flexible Configuration:** Customize models, parameters (like `temperature`), and behavior via commands or environment variables.
*   **🧩 Adapter System:** Supports different LLM backends (currently Direct OpenAI-compatible API access, with LangChain integration).
*   **🏷️ Model Mapping:** Use short aliases (like `g4o`) for full model names (`gpt-4o`).
*   **📊 Status & Cost Tracking:** Get immediate feedback on prompt execution time, token usage, and estimated cost.
*   **🔄 Jira Integration:** Fetch Jira tickets directly into your notebook to use as context for your LLM queries.
*   **📝 Confluence Wiki Integration:** Import wiki pages directly into your notebook to use as context for your LLM prompts.
*   **🦊 GitLab Integration:** Import repositories and merge requests as context for your LLM prompts, with token size estimates.
*   **🐱 GitHub Integration:** Import repositories and pull requests as context for your LLM prompts, with token size estimates.
*   **🌐 WebContent Integration:** Fetch, clean, and extract content from websites to use as context for your LLM prompts.
*   **📄 Google Docs Integration:** Import content from Google Documents directly into your LLM context.

---

## 🚀 Installation

**Requirements:** Python 3.9+

Install Cellmage using pip:

```bash
pip install cellmage
```

*(Optional)* To use the LangChain adapter, install with the extra dependencies:

```bash
pip install "cellmage[langchain]"
```

*(Optional)* For Jira integration:

```bash
pip install "cellmage[jira]"
```

*(Optional)* For GitLab integration:

```bash
pip install "cellmage[gitlab]"
```

*(Optional)* For Confluence integration:

```bash
pip install "cellmage[confluence]"
```

*(Optional)* For WebContent integration:

```bash
pip install "cellmage[webcontent]"
```

*(Optional)* For Google Docs integration:

```bash
pip install "cellmage[gdocs]"
```

*(Optional)* For all features:

```bash
pip install "cellmage[all]"
```

*(Optional)* For development or to get the latest code, install from source:

```bash
git clone https://github.com/madpin/cellmage.git
cd cellmage
pip install -e .[dev] # Includes dev dependencies
```

---

## ⚡ Quick Start: Your First Spell

1.  **Load the Magic:** In a Jupyter or IPython cell, load the extension:
    ```python
    %load_ext cellmage
    ```

2.  **Configure API Key (One-time Setup):**
    Cellmage needs your LLM provider's API key. It looks for it in this order:
    *   `CELLMAGE_API_KEY` environment variable
    *   `OPENAI_API_KEY` environment variable
    *   You can also set it via `%llm_config --set-override api_key YOUR_KEY`, but environment variables (e.g., in a `.env` file) are recommended for security.
    *   Similarly, set `CELLMAGE_API_BASE` or `OPENAI_API_BASE` if using a non-OpenAI endpoint.

3.  **Cast Your First `%%llm` Spell:**
    ```python
    %%llm -m gpt-4o-mini
    Explain the concept of "duck typing" in Python using a simple analogy.
    ```
    *(This sends the text below `%%llm` as a prompt to the `gpt-4o-mini` model.)*

4.  **See the Magic Happen:** The LLM's response will appear below the cell, along with status info (time, tokens, cost). ✨

5.  **Troubleshooting:** If you see an error like `Line magic function '%llm_config' not found`, make sure you've loaded the extension correctly using the exact path shown in step 1.

---

## 📚 Core Concepts & Examples

### 1. Magic Commands

*   `%load_ext cellmage`: Loads the extension (usually run once per session).
*   `%%llm`: Executes the entire cell content as a prompt to the configured LLM.
    ```python
    %%llm --temperature 0.8 --model gpt-4o
    Write a short, futuristic story about a programmer in Dublin discovering sentient pão de queijo. Use a slightly humorous tone.
    ```
    *(Flags like `--temperature` or `--model` temporarily override settings for this specific call.)*

*   `%llm_config`: Manages the session state, default model, personas, history, etc.
    ```python
    # See current status (active persona, model, overrides)
    %llm_config --status

    # Set the default model for subsequent %%llm calls
    %llm_config --model gpt-4o

    # List available personas
    %llm_config --list-personas

    # Activate the 'python_expert' persona
    %llm_config --persona python_expert

    # Clear the conversation history
    %llm_config --clear-history
    ```
    *(Run `%llm_config --help` for all options!)*

### 2. Personas (Your AI's Identities)

Personas define the LLM's system prompt and default parameters.

*   **Using a Persona:**
    ```python
    # Activate globally
    %llm_config --persona data_scientist

    # Use just for one cell
    %%llm -p code_reviewer
    Review this Python function for potential bugs and style issues:
    ```
    ```python
    def calc(a,b): return a+b
    ```

*   **Creating Personas:**
    Create Markdown files (e.g., `my_persona.md`) in an `llm_personas` directory in your notebook's working directory (or configure `CELLMAGE_PERSONAS_DIRS`).

    **Example (`llm_personas/code_reviewer.md`):**
    ```markdown
    ---
    name: Code Reviewer Bot
    model: gpt-4o-mini # Default model for this persona
    temperature: 0.3   # Default temperature
    description: Reviews code for quality and correctness.
    ---
    You are a meticulous code reviewer. Analyze the provided code snippets.
    Identify potential bugs, style inconsistencies (PEP 8), and suggest improvements
    for clarity, efficiency, and robustness. Be constructive and provide clear examples.
    ```

### 3. Ambient Mode (The "Always-On" Charm)

Make *every* standard cell an LLM prompt without typing `%%llm`.

*   **Activate:**
    ```python
    # Activate ambient mode, optionally setting defaults
    %llm_config_persistent --model gpt-4o-mini --persona helpful_assistant
    ```
    *(Now, just type your prompt in a cell and run it!)*

*   **Execute Python Code While Ambient:** Use `%%py`:
    ```python
    %%py
    # This runs as normal Python, not an LLM prompt
    import pandas as pd
    print(f"Pandas version: {pd.__version__}")
    ```

*   **Deactivate:**
    ```python
    %disable_llm_config_persistent
    ```

    > **⚠️ Warning:** Ambient mode might interfere with some IDE features like autocomplete in certain environments, as it intercepts cell execution. If you experience issues, disable ambient mode and use the explicit `%%llm` magic.

### 4. Snippets (Reusable Context Blocks)

Inject files as context (e.g., code definitions, instructions) into your prompts.

*   **Creating Snippets:**
    Save text/code into files (e.g., `my_context.py`) in an `llm_snippets` directory.

*   **Using Snippets:**
    ```python
    # Add content of 'my_utils.py' as a user message before the main prompt
    %llm_config --snippet my_utils.py

    # Add 'system_instructions.md' as a system message
    %llm_config --sys-snippet system_instructions.md

    %%llm
    Based on the utility functions and instructions provided, write a function that uses `calculate_metrics` from the utils.
    ```
    *(Snippets added via `%llm_config` persist until cleared or new snippets are added.)*
    *You can also add snippets per-cell using `%%llm --snippet ...`.*

### 5. Session Management (Saving Your Work)

Cellmage automatically saves conversations if an `llm_conversations` directory exists. You can also manually save/load.

```python
# Save the current conversation (uses timestamp and first words if no name given)
%llm_config --save "data_analysis_session"

# Load a previously saved session
%llm_config --load "data_analysis_session_20250428_...."

# List saved sessions
%llm_config --list-sessions
```

### 6. Jira Integration

Connect your notebooks directly to Jira tickets using the `%jira` magic command.

*   **Installation:**
    ```bash
    pip install "cellmage[jira]"
    ```

*   **Configuration:**
    Set these environment variables in a `.env` file or your environment:
    ```
    JIRA_URL=https://your-company.atlassian.net
    JIRA_USER_EMAIL=your.email@company.com
    JIRA_API_TOKEN=your_jira_api_token
    ```

*   **Basic Usage:**
    ```python
    # Fetch a specific ticket and add it to chat history
    %jira PROJECT-123

    # Fetch a ticket and add as system context
    %jira PROJECT-123 --system

    # Just display a ticket without adding to history
    %jira PROJECT-123 --show

    # Use JQL to fetch multiple tickets
    %jira --jql 'assignee = currentUser() ORDER BY updated DESC' --max 5
    ```

*   **Using with LLM Queries:**
    ```python
    # First, fetch the ticket
    %jira PROJECT-123

    # Then, reference it in your prompt
    %%llm
    Given the Jira ticket above, what are the key requirements I need to implement?
    ```

### 7. GitLab Integration

Fetch GitLab repositories and merge requests directly into your notebook using the `%gitlab` magic command.

*   **Installation:**
    ```bash
    pip install "cellmage[gitlab]"
    ```

*   **Configuration:**
    Set these environment variables in a `.env` file or your environment:
    ```
    GITLAB_URL=https://gitlab.com
    GITLAB_PAT=your_gitlab_personal_access_token
    ```

*   **Basic Usage:**
    ```python
    # Fetch a repository and add it to chat history
    %gitlab namespace/project

    # Fetch a repository and add as system context
    %gitlab namespace/project --system

    # Just display a repository without adding to history
    %gitlab namespace/project --show

    # Fetch a merge request and add to chat history
    %gitlab namespace/project --mr 123

    # Include full code content (may be very large)
    %gitlab namespace/project --full-code

    # Get more detailed contributor information
    %gitlab namespace/project --contributors-months 12
    ```

*   **Using with LLM Queries:**
    ```python
    # First, fetch the repository
    %gitlab namespace/project

    # Check the estimated token size in the output
    # "✅ Estimated token size: ~12,345 tokens (10,000 code, 2,345 metadata)"

    # Then, reference it in your prompt
    %%llm
    Based on the GitLab repository above, can you explain the architecture of this project?
    ```

### 8. GitHub Integration

Fetch GitHub repositories and pull requests directly into your notebook using the `%github` magic command.

*   **Installation:**
    ```bash
    pip install "cellmage[github]"
    ```

*   **Configuration:**
    Set these environment variables in a `.env` file or your environment:
    ```
    GITHUB_TOKEN=your_github_personal_access_token
    ```

*   **Basic Usage:**
    ```python
    # Fetch a repository and add it to chat history
    %github username/repo

    # Fetch a repository and add as system context
    %github username/repo --system

    # Just display a repository without adding to history
    %github username/repo --show

    # Fetch a pull request and add to chat history
    %github username/repo --pr 123

    # Include full code content (may be very large)
    %github username/repo --full-code

    # Get more detailed contributor information
    %github username/repo --contributors-months 12
    ```

*   **Using with LLM Queries:**
    ```python
    # First, fetch the repository
    %github username/repo

    # Check the estimated token size in the output
    # "✅ Estimated token size: ~12,345 tokens (10,000 code, 2,345 metadata)"

    # Then, reference it in your prompt
    %%llm
    Based on the GitHub repository above, can you analyze the code architecture and suggest improvements?
    ```

### 9. Confluence Wiki Integration

Connect your notebooks directly to Confluence wiki content using the `%confluence` magic command.

*   **Installation:**
    ```bash
    pip install "cellmage[confluence]"
    ```

*   **Configuration:**
    Set these environment variables in a `.env` file or your environment:
    ```
    CONFLUENCE_URL=https://your-company.atlassian.net
    # Confluence uses Jira credentials
    JIRA_USER_EMAIL=your.email@company.com
    JIRA_API_TOKEN=your_jira_api_token
    ```

*   **Basic Usage:**
    ```python
    # Fetch a page by space key and title (handles spaces in title correctly)
    %confluence SPACE:Page Title

    # Fetch a page by its ID
    %confluence 123456789

    # Fetch a page and add as system context
    %confluence SPACE:Page Title --system

    # Just display a page without adding to history
    %confluence SPACE:Page Title --show

    # Use CQL (Confluence Query Language) to fetch multiple pages
    %confluence --cql "space = SPACE AND title ~ 'Search Term'" --max 5
    ```

*   **Using with LLM Queries:**
    ```python
    # First, fetch the wiki page
    %confluence SPACE:Project Documentation

    # Then, reference it in your prompt
    %%llm
    Based on the Confluence page above, what are the key requirements for this project?
    ```

### 10. WebContent Integration

Fetch, clean, and extract content from websites directly into your notebook using the `%webcontent` magic command.

*   **Installation:**
    ```bash
    pip install "cellmage[webcontent]"
    ```

*   **Dependencies:**
    The WebContent integration requires additional Python libraries:
    ```bash
    pip install requests beautifulsoup4 markdownify trafilatura
    ```

*   **Basic Usage:**
    ```python
    # Fetch website content and add it to chat history
    %webcontent https://example.com

    # Fetch content and add as system context
    %webcontent https://example.com --system

    # Just display content without adding to history
    %webcontent https://example.com --show

    # Get raw HTML content without cleaning
    %webcontent https://example.com --raw
    ```

*   **Advanced Options:**
    ```python
    # Use a specific extraction method (trafilatura, bs4, or simple)
    %webcontent https://example.com --method bs4

    # Include image references in the output
    %webcontent https://example.com --include-images

    # Remove hyperlinks from the output
    %webcontent https://example.com --no-links

    # Set a custom timeout for the request
    %webcontent https://example.com --timeout 60
    ```

*   **Using with LLM Queries:**
    ```python
    # First, fetch the website content
    %webcontent https://example.com

    # Then, reference it in your prompt
    %%llm
    Summarize the key points from the website content above and highlight the most important information.
    ```

### 11. Google Docs Integration

Fetch content from Google Documents directly into your notebook using the `%gdocs` magic command.

*   **Installation:**
    ```bash
    pip install "cellmage[gdocs]"
    ```

*   **Configuration:**
    Set these environment variables in a `.env` file or your environment:
    ```
    # OAuth configuration (default)
    CELLMAGE_GDOCS_AUTH_TYPE=oauth
    CELLMAGE_GDOCS_TOKEN_PATH=~/.cellmage/gdocs_token.pickle
    CELLMAGE_GDOCS_CREDENTIALS_PATH=~/.cellmage/gdocs_credentials.json

    # Or service account configuration
    CELLMAGE_GDOCS_AUTH_TYPE=service_account
    CELLMAGE_GDOCS_SERVICE_ACCOUNT_PATH=~/.cellmage/gdocs_service_account.json
    ```

*   **Basic Usage:**
    ```python
    # Fetch a Google Document by its ID and add it to chat history
    %gdocs your_google_doc_id

    # Fetch a document using its URL
    %gdocs https://docs.google.com/document/d/YOUR_DOC_ID/edit

    # Fetch a Google Document and add as system context
    %gdocs your_google_doc_id --system

    # Just display the content of a Google Document without adding to history
    %gdocs your_google_doc_id --show

    # Use a specific authentication type
    %gdocs your_google_doc_id --auth-type service_account
    ```

*   **Searching for Documents:**
    ```python
    # Search for documents by content or title
    %gdocs --search "project documentation"

    # Filter search results
    %gdocs --search "project documentation" --author "user@example.com"
    %gdocs --search "project documentation" --created-after "last week"
    %gdocs --search "project documentation" --modified-before "2023-12-31"

    # Fetch content from search results (default: top 3)
    %gdocs --search "project documentation" --content
    %gdocs --search "project documentation" --content --max-content 5
    ```

*   **Using with LLM Queries:**
    ```python
    # First, fetch the Google Document
    %gdocs your_google_doc_id

    # Then, reference it in your prompt
    %%llm
    Based on the Google Document above, summarize the key points and provide actionable insights.
    ```

### 12. SQLite Storage

CellMage now uses SQLite as the default storage backend for improved performance and reliability:

* **Automatic:** SQLite storage is used by default - no configuration needed
* **Persistent:** Your conversation history is automatically saved and can be restored across sessions
* **Faster:** Better performance for larger conversation histories compared to file-based storage
* **Reliable:** Transactions ensure that your data is safely stored

To use SQLite-specific features:

```python
# Load the SQLite-specific magic commands
%load_ext cellmage.integrations.sqlite_magic

# List all stored conversations in the database
%sqlite_llm --list-conversations

# View details about a specific conversation
%sqlite_llm --conversation-info conversation_id

# Export a conversation to JSON
%sqlite_llm --export conversation_id output.json
```

---

## ⚙️ Configuring the Base Directory for Working Files

CellMage stores working files (personas, snippets, logs, .data, etc.) in a base directory. By default, this is the current working directory, but you can control it globally using the `CELLMAGE_BASE_DIR` environment variable:

```bash
export CELLMAGE_BASE_DIR=/path/to/your/project
```

All CellMage working files and directories (e.g., `llm_personas`, `llm_snippets`, `.data`, `cellmage.log`) will be created and accessed under this base directory. This makes it easy to colocate CellMage files with your Jupyter notebooks or to centralize them for multiple projects.

**Backward Compatibility:**
- If `CELLMAGE_BASE_DIR` is not set, CellMage will continue to use the current working directory as before.
- You can migrate existing files by moving them to your chosen base directory.

**Migration Example:**
```bash
# Move your existing working files to the new base directory
export CELLMAGE_BASE_DIR=~/my_notebook_project
mkdir -p $CELLMAGE_BASE_DIR
mv llm_personas llm_snippets .data cellmage.log $CELLMAGE_BASE_DIR/
```

See the [troubleshooting guide](docs/source/troubleshooting.md) and tutorials for more details.

---

## ⚙️ Configuration

Cellmage is configured via:

1.  **Environment Variables:** (Prefix `CELLMAGE_`) - e.g., `CELLMAGE_API_KEY`, `CELLMAGE_DEFAULT_MODEL`, `CELLMAGE_PERSONAS_DIRS`. Recommended for secrets.
    - **Custom Headers:** Set custom headers for LLM requests using the `CELLMAGE_HEADER_` prefix. For example, `CELLMAGE_HEADER_X_REDACT_ALLOW="LOCATION,PERSON"` will send the header `x-redact-allow: LOCATION,PERSON` with LLM requests. Header names are automatically converted from environment variable format to proper HTTP header format (lowercase with hyphens instead of underscores).
2.  **`.env` File:** Place a `.env` file in your working directory.
3.  **Magic Commands:** `%llm_config` allows runtime changes.

Full configuration options:

```
CELLMAGE_API_KEY          - Your LLM API key
CELLMAGE_API_BASE         - API base URL (default: https://api.openai.com/v1)
CELLMAGE_DEFAULT_MODEL    - Default model (e.g., gpt-4o-mini)
CELLMAGE_PERSONAS_DIRS    - Comma-separated paths to persona directories
CELLMAGE_SNIPPETS_DIRS    - Comma-separated paths to snippet directories
CELLMAGE_CONVERSATIONS_DIR - Directory for saving conversations
CELLMAGE_SQLITE_PATH      - Custom path for SQLite database (default: ~/.cellmage/conversations.db)
CELLMAGE_ADAPTER          - LLM adapter type (direct or langchain)
CELLMAGE_BASE_DIR         - Base directory for all working files (default: current working directory)
```

---

## 🗺️ Roadmap & Contributing

Cellmage is actively developed. Future ideas include:

*   More LLM adapters (Anthropic, Gemini, local models).
*   Better error handling and feedback.
*   Visual configuration options.
*   Deeper notebook state integration.
*   Improved integration with tools like GitHub Copilot and LangChain.

Contributions, bug reports, and feature requests are welcome! Please check the `CONTRIBUTING.md` file and open an issue or PR on GitHub:

➡️ [**GitHub Repository: madpin/cellmage**](https://github.com/madpin/cellmage)

---

## 🧑‍💻 About the Author

Crafted with ❤️ and 🥤 in Dublin, Ireland 🇮🇪 by **Thiago MadPin**.

*   Staff Software Engineer @ Indeed
*   Passionate about Data Intelligence, Python, Leadership, and Geek Culture (Matrix, One Piece, Asimov fan!)
*   Lover of Dublin life, Sano Pizza 🍕, Pão de Queijo 🧀, and walks near St. Patrick's Cathedral.

---

## 📜 License

Cellmage is released under the **MIT License**. See the `LICENSE` file for details.
