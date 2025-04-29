# 🪄 Cellmage: Your Notebook LLM Wizard 🎩

**Tired of wrestling with LLM APIs in your notebooks? Cellmage seamlessly integrates Large Language Models (LLMs) directly into your Jupyter/IPython workflow.**

Stop copy-pasting, managing complex client code, or losing context. Cellmage provides intuitive magic commands (`%%llm`, `%llm_config`) to chat with models, manage conversation history, switch personas, inject context snippets, and even enable an "ambient" mode where *every* cell becomes an LLM prompt!

It's designed for **data scientists, software engineers, researchers, and students** who want to leverage LLMs *within* their existing notebook environment with minimal friction. Spend less time on boilerplate, more time on solving actual problems (or generating cool sci-fi plots, we don't judge!).

[![PyPI version](https://badge.fury.io/py/cellmage.svg)](https://badge.fury.io/py/cellmage)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation Status](https://readthedocs.org/projects/cellmage/badge/?version=latest)](https://cellmage.readthedocs.io/en/latest/?badge=latest)

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

---

## 🚀 Installation

**Requirements:** Python 3.8+

Install Cellmage using pip:

```bash
pip install cellmage
```

*(Optional)* To use the LangChain adapter, install with the extra dependencies:

```bash
pip install "cellmage[langchain]"
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

---

## ⚙️ Configuration

Cellmage is configured via:

1.  **Environment Variables:** (Prefix `CELLMAGE_`) - e.g., `CELLMAGE_API_KEY`, `CELLMAGE_DEFAULT_MODEL`, `CELLMAGE_PERSONAS_DIRS`. Recommended for secrets.
    - **Custom Headers:** Set custom headers for LLM requests using the `CELLMAGE_HEADER_` prefix. For example, `CELLMAGE_HEADER_X_REDACT_ALLOW="LOCATION,PERSON"` will send the header `x-redact-allow: LOCATION,PERSON` with LLM requests. Header names are automatically converted from environment variable format to proper HTTP header format (lowercase with hyphens instead of underscores).
2.  **`.env` File:** Place a `.env` file in your working directory.
3.  **Magic Commands:** `%llm_config` allows runtime changes.

*(See `config.py` or documentation for all options.)*

---

## 🗺️ Roadmap & Contributing

Cellmage is actively developed. Future ideas include:

*   More LLM adapters (Anthropic, Gemini, local models).
*   Better error handling and feedback.
*   Visual configuration options.
*   Deeper notebook state integration.

Contributions, bug reports, and feature requests are welcome! Please check the `CONTRIBUTING.md` file and open an issue or PR on GitHub:

➡️ [**GitHub Repository: madpin/cellmage**](https://github.com/madpin/cellmage)

---

## 🧑‍💻 About the Author

Crafted with ❤️ and ☕ in Dublin, Ireland 🇮🇪 by **Thiago MadPin**.

*   Staff Software Engineer @ Indeed
*   Passionate about Data Intelligence, Python, Leadership, and Geek Culture (Matrix, One Piece, Asimov fan!)
*   Lover of Dublin life, Sano Pizza 🍕, Pão de Queijo 🧀, and walks near St. Patrick's Cathedral.

---

## 📜 License

Cellmage is released under the **MIT License**. See the `LICENSE` file for details.