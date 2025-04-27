# 🧙 CellMage IPython Magic Commands

CellMage provides a set of powerful IPython magic commands that enable you to interact with Large Language Models (LLMs) directly within your Jupyter or IPython notebooks. This document provides a comprehensive reference for all available magic commands and their arguments.

## Loading the Extension

Before using any of the magic commands, you need to load the CellMage extension in your notebook:

```python
%load_ext cellmage
```

## Available Magic Commands

CellMage provides the following magic commands:

1. `%llm_config` - Configure the LLM session state and manage resources
2. `%llm_config_persistent` - Configure the LLM session and enable ambient mode
3. `%disable_llm_config_persistent` - Disable ambient mode
4. `%%llm` - Execute a cell as an LLM prompt
5. `%%py` - Execute a cell as normal Python code (when ambient mode is active)

## Detailed Command Reference

### 1. `%llm_config`

The `%llm_config` line magic is used to configure your LLM session state and manage resources.

```python
%llm_config [arguments]
```

#### Available Arguments

| Argument | Description |
|----------|-------------|
| `-p`, `--persona` | Select and activate a persona by name |
| `--show-persona` | Show the currently active persona details |
| `--list-personas` | List all available persona names |
| `--set-override KEY VALUE` | Set a temporary LLM param override (e.g., `--set-override temperature 0.5`) |
| `--remove-override KEY` | Remove a specific override key |
| `--clear-overrides` | Clear all temporary LLM param overrides |
| `--show-overrides` | Show the currently active overrides |
| `--clear-history` | Clear the current chat history (keeps system prompt) |
| `--show-history` | Display the current message history |
| `--save [FILENAME]` | Save session. If no name is provided, uses current session ID. '.md' added automatically |
| `--load SESSION_ID` | Load session from specified identifier (filename without .md) |
| `--list-sessions` | List saved session identifiers |
| `--auto-save` | Enable automatic saving of conversations to the conversations directory |
| `--no-auto-save` | Disable automatic saving of conversations |
| `--list-snippets` | List available snippet names |
| `--snippet NAME` | Add user snippet content before sending prompt (can be used multiple times) |
| `--sys-snippet NAME` | Add system snippet content before sending prompt (can be used multiple times) |
| `--status` | Show current status (persona, overrides, history length) |
| `--model NAME` | Set the default model for the LLM client |
| `--adapter {direct,langchain}` | Switch to a different LLM adapter implementation |

#### Examples

```python
# Set a specific persona
%llm_config --persona python_expert

# Change the default model
%llm_config --model gpt-4o

# Set a parameter override
%llm_config --set-override temperature 0.7

# Add a snippet to be included in the next LLM request
%llm_config --snippet code_context.py

# Show current session status
%llm_config --status

# Switch to a different adapter
%llm_config --adapter langchain
```

### 2. `%llm_config_persistent`

The `%llm_config_persistent` line magic has the same functionality as `%llm_config` but also enables "ambient mode," which processes all regular code cells as LLM prompts. Note that the `--adapter` parameter is not available for this command.

```python
%llm_config_persistent [arguments]
```

When ambient mode is active, any cell you execute that doesn't start with a magic command (`%` or `%%`) or shell command (`!`) will be sent as a prompt to the LLM, and the response will be displayed below the cell.

#### Available Arguments

All the same arguments as `%llm_config` except for `--adapter`.

#### Example

```python
# Enable ambient mode with a specific persona
%llm_config_persistent --persona coding_assistant --model gpt-4o
```

After running this command, you can simply type a prompt in a regular cell (no `%%llm` needed) and run it to get a response from the LLM.

### 3. `%disable_llm_config_persistent`

This line magic disables ambient mode, returning to normal cell execution behavior.

```python
%disable_llm_config_persistent
```

### 4. `%%llm`

The `%%llm` cell magic allows you to send the cell content as a prompt to the LLM.

```python
%%llm [arguments]
Your prompt text here...
```

#### Available Arguments

| Argument | Description |
|----------|-------------|
| `-p`, `--persona` | Use specific persona for THIS call only |
| `-m`, `--model` | Use specific model for THIS call only |
| `-t`, `--temperature` | Set temperature for THIS call |
| `--max-tokens` | Set max_tokens for THIS call |
| `--no-history` | Do not add this exchange to history |
| `--no-stream` | Do not stream output (wait for full response) |
| `--no-rollback` | Disable auto-rollback check for this cell run |
| `--param KEY VALUE` | Set any other LLM param ad-hoc (e.g., `--param top_p 0.9`). Can be used multiple times |
| `--list-snippets` | List available snippet names |
| `--snippet NAME` | Add user snippet content before sending prompt (can be used multiple times) |
| `--sys-snippet NAME` | Add system snippet content before sending prompt (can be used multiple times) |

#### Examples

```python
%%llm --persona data_scientist --model gpt-4o
Explain the concept of p-values in statistics in simple terms.
```

```python
%%llm -t 0.8 --param top_p 0.95
Generate a creative story about a wizard who codes in Python.
```

### 5. `%%py`

The `%%py` cell magic executes the cell as normal Python code, bypassing ambient mode. This is useful when ambient mode is enabled but you want to execute a specific cell as regular Python code without LLM processing.

```python
%%py
# This code will run as normal Python
x = 10
print(f"The value is {x}")
```

## Ambient Mode

Ambient mode is a powerful feature that, when enabled, allows any regular cell to be automatically processed as an LLM prompt. This eliminates the need to prepend each prompt with `%%llm`.

- To enable ambient mode: `%llm_config_persistent`
- To disable ambient mode: `%disable_llm_config_persistent`

When ambient mode is active, cells that start with magics (`%`, `%%`) or shell commands (`!`) are still executed normally, but all other cells are sent to the LLM.

If you need to execute Python code while ambient mode is active, use the `%%py` cell magic.

> **⚠️ Warning:** Ambient mode may intercept Jupyter's internal background functions like `__jupyter_exec_background__()` which are used for autocomplete and other IDE features. If you notice unexpected behavior (such as code completion not working properly or internal Jupyter commands being sent to the LLM as prompts), disable ambient mode using `%disable_llm_config_persistent` and use explicit `%%llm` cell magic instead.

## Status Information

After each successful LLM call (via `%%llm` or ambient mode), a status bar is displayed showing:

- Success indicator (✅)
- Duration of the call (⏱️)
- Token counts (input/output) (📥/📤)
- Estimated cost (🪙)
- Model used

This information helps you track your LLM usage and costs.