# 🧙 CellMage ✨

[![PyPI version](https://badge.fury.io/py/cellmage.svg)](https://badge.fury.io/py/cellmage) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
**Stop juggling browser tabs! Start casting LLM spells directly in your Jupyter Notebook cells!**

<p align="center">
  <img src="docs/images/cellmage_logo.png" alt="CellMage Logo Concept" width="200"/>
</p>

Ever find yourself deep in a complex data analysis or coding session, only to hit a wall? You need a quick code snippet, an explanation, or just some creative brainstorming juice from your favorite Large Language Model. But *ugh*, that means breaking your flow, opening a new tab, copying, pasting, context-switching... the magic is *gone*.

**Fear not, apprentice! CellMage is here to restore the enchantment!** 🪄

CellMage is your personal LLM wizard, living right inside your Jupyter or IPython notebook. It provides powerful, intuitive magic commands to interact with LLMs without ever leaving your cell-based sanctuary.

## What Sorcery is This? (Core Features)

CellMage isn't *actual* magic, but it feels pretty close:

* ✨ **Intuitive Spellcasting:** Use the `%%llm` cell magic. Write your prompt, run the cell, and *poof* – the LLM's response appears!
* 📜 **Arcane History Scrolls:** CellMage remembers your conversation. Even better, it detects when you re-run a cell and cleverly avoids duplicating history. Like turning back time, but less paradoxical!
* 🔮 **Persona Grimoires:** Define different LLM "personalities" (system prompts + configs) in simple Markdown files. Need a Python expert? A terse code generator? A rubber duck? Switch personas with a simple command!
* 🌍 **Access Diverse Magical Fonts:** Connect to OpenAI, Anthropic, Azure, and other OpenAI-compatible APIs.
* ⚡️ **Live Conjuring:** Watch the LLM weave its response character-by-character with built-in streaming support (the default!).
* 🪄 **Ambient Enchantment (Optional):** Feeling lazy? Use `%llm_setup_forever` to automatically treat *any* standard cell you run as a prompt! (Use `%disable_llm_config_persistent` to turn it off).
* 🧪 **Precise Incantations:** Override models, temperature, and other parameters on-the-fly for specific spells or configure instance-wide defaults. Use model aliases (like 'g4' for 'gpt-4') for quick access to your favorite models.
* 📝 **Model Aliases:** Define short aliases for your frequently used models in a `cellmage_models.yml` file or manage them through magic commands.
* GOTO **Re-usable Spell Snippets:** Inject content from local files (like code context or data samples) directly into the conversation history before casting your spell.
* 💰 **Mana Tracking:** Get a handy status bar after each call showing duration and estimated cost (because even magic has its price!).
* 📚 **Detailed Spell Logs:** Keep a record of your magical experiments with robust file logging.

## The Installation Incantation 🪄

Ready to wield this power? Open your terminal and chant the sacred words:

```bash
# Basic installation
pip install cellmage

# For LangChain integration
pip install "cellmage[langchain]"
```

## LLM Connection Options 🔌

CellMage provides a DirectLLMAdapter for connecting to LLM APIs:

**DirectLLMAdapter** (built-in with no additional dependencies): 
- Connects directly to OpenAI-compatible APIs via standard HTTP requests
- Supports standard OpenAI API functionality including streaming
- Simple and reliable with minimal dependencies

## Summoning Your First Spell (Quick Start) ⚡️

1.  **Load the Extension:** In a notebook cell, run:
    ```python
    %load_ext cellmage
    ```

2.  **Configure (Optional but Recommended):** Tell CellMage where to find its power source. Set your API key and base URL (if needed) using environment variables (`CELLMAGE_API_KEY`, `CELLMAGE_API_BASE`) or the setup magic:
    ```python
    # Example for a local OpenAI-compatible API server
    %llm_setup --api_base http://localhost:1234/v1 --default_model local-model
    ```
    *Or for OpenAI:*
    ```python
    # Make sure CELLMAGE_API_KEY is set as an environment variable, or use:
    # %llm_setup --api_key "sk-..." --default_model gpt-4o
    ```
    *(See "Connecting to Magical Fonts" below for more ways)*

3.  **Cast Your Spell!** In a new cell, use the `%%llm` magic:
    ```python
    %%llm
    Explain the difference between a list and a tuple in Python like I'm five.
    ```
    Run the cell and behold the LLM's wisdom appearing below! ✨

## Mastering the Arcane Arts (Core Concepts) 📖

### Available Magic Commands

CellMage provides the following IPython magic commands:

* `%%llm` - Cell magic to send your prompt to the LLM
* `%llm_config` - Line magic to configure session state and manage resources 
* `%llm_config_persistent` - Enable ambient mode (process regular cells as LLM prompts)
* `%disable_llm_config_persistent` - Disable ambient mode
* `%%py` - Execute a cell as normal Python code when ambient mode is active

For a comprehensive reference of all available magic commands and their arguments, see the [IPython Magic Commands documentation](docs/source/ipython_magic_commands.md).

### The `%%llm` Cell Spell

This is your bread-and-butter. Anything in a cell marked with `%%llm` at the top gets sent as a prompt to the currently configured LLM.

```python
%%llm --model gpt-4o --persona python_expert
Write a python function that takes a list of numbers and returns the sum,
but handle potential type errors gracefully.
```

Common arguments:
* `-p`, `--persona`: Temporarily use a different personality for this spell
* `-m`, `--model`: Temporarily use a different model for this spell
* `-t`, `--temperature`: Set temperature for this call
* `--max-tokens`: Set max_tokens for this call
* `--no-stream`: Disable streaming output just for this cell
* `--no-history`: Don't add this exchange to conversation history
* `--param KEY VALUE`: Set any other LLM param ad-hoc (e.g., `--param top_p 0.9`)

### Configuring Your Session (`%llm_config` & `%llm_config_persistent`)

* `%llm_config`: Configure CellMage for the current session. Set defaults like your preferred model, API endpoints, persona folders, logging preferences, etc.
    ```python
    %llm_config --model gpt-4o --persona coding_assistant --auto_save True --status
    ```
* `%llm_config_persistent`: Does the same as `%llm_config`, *but also* enables the "Ambient Enchantment" mode, treating subsequent non-magic cells as prompts. Great for pure chat sessions! Use `%disable_llm_config_persistent` to deactivate.

### Model Aliases

CellMage supports defining short aliases for model names. You can:

1. Create a `cellmage_models.yml` file in your project directory:
```yaml
# Model aliases
g4: gpt-4
g4t: gpt-4-turbo
c2: claude-2
```

2. Manage aliases through magic commands:
```python
%llm_config --list-mappings  # Show current mappings
%llm_config --add-mapping g4 gpt-4  # Add new mapping
%llm_config --remove-mapping g4  # Remove mapping
```

Then use your aliases anywhere you'd use a model name:
```python
%llm_config --model g4  # Use GPT-4
%%llm -m g4t  # Use GPT-4 Turbo for this cell
```

### Ambient Enchantment (Auto-Processing)

Run `%llm_config_persistent`. Now, just type a prompt in a regular cell and run it! CellMage intercepts it and sends it to the LLM. Magic!

To run actual Python code while in ambient mode, use the `%%py` cell magic:

```python
%%py
# This will run as normal Python code, not as an LLM prompt
x = 10
print(f"The value is {x}")
```

Remember to use `%disable_llm_config_persistent` when you want normal cell execution back.

### Spell Snippets

Need to include the content of a file (like code context or data) in your prompt history *before* asking your question?

```python
# Add content of my_code.py as a system message before the next %%llm call
%llm_setup --snippets my_code.py system

# Or add multiple files with a specific role
# %llm_setup --snippets file1.txt file2.json user
```

The snippet content will be added to the history for the *next* LLM call.

### Multiple Persona and Snippet Folders

CellMage supports using personas and snippets from multiple directories, making it easier to organize resources by project or purpose:

1. **Environment Variables**: Set additional directories using comma-separated values:
   ```bash
   # Using environment variables
   export CELLMAGE_PERSONAS_DIRS=project_A/personas,project_B/personas
   export CELLMAGE_SNIPPETS_DIRS=project_A/snippets,project_B/snippets
   ```

2. **Auto-discovery**: CellMage automatically looks for personas and snippets in standard locations:
   - Root `llm_personas` and `llm_snippets` directories
   - `notebooks/llm_personas`, `notebooks/llm_snippets`
   - `notebooks/examples` and `notebooks/tests` subdirectories

3. **Custom Loaders**: For programmatic access to multiple directories:
   ```python
   from cellmage.resources.file_loader import MultiFileLoader
   
   # Create a loader with multiple directories
   loader = MultiFileLoader(
       personas_dirs=["llm_personas", "project_A/personas"], 
       snippets_dirs=["llm_snippets", "project_A/snippets"]
   )
   
   # See available resources
   print(f"Available personas: {loader.list_personas()}")
   print(f"Available snippets: {loader.list_snippets()}")
   ```

### Mana Tracking (Status Bar)

After each successful call, a small status bar appears showing:
✅ Success | ⏱️ Duration | 📥 Tokens In | 📤 Tokens Out | 🪙 Estimated Cost

*(Cost estimation is basic and may vary wildly based on the model/provider)*

## Advanced Spellcraft

*(Add examples here later for things like programmatic use, complex overrides, etc.)*

```python
# Example: Accessing the underlying object (if needed)
from cellmage import NotebookLLMMagics # Assuming this path
mage_instance = %magics_object NotebookLLMMagics
llm_helper = mage_instance.llm

# Now you can use methods directly
# llm_helper.set_override("temperature", 0.9)
# response = llm_helper.chat("This uses the override", personality_name="creative")
# llm_helper.remove_override("temperature")
```

## Join the Coven? (Contributing)

Found a mischievous bug? Have an idea for a powerful new spell? Contributions are welcome! Please check the `CONTRIBUTING.md` file for guidelines.

## The Fine Print (License)

CellMage is distributed under the MIT License. See `LICENSE` file for details. May cause spontaneous bursts of productivity and/or delight. Not responsible for accidentally summoning sentient code.

---

**Happy Conjuring!** ✨
