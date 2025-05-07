# 🧙 The Spell Book: CellMage Magic Commands

Welcome to the official spell book of CellMage! Here you'll find all the magical incantations (IPython magic commands) that allow you to summon the power of Large Language Models directly within your enchanted notebooks. Master these spells to become a true wizard of AI!

## 📜 Summoning the Magic

Before casting any spells, you must first invite the magical presence into your notebook:

```ipython
%load_ext cellmage.integrations.ipython_magic
```

## 🪄 Your Magical Arsenal

The CellMage grimoire contains these powerful spells:

1. `%llm_config` - Configure your magical powers and manage your arcane resources
2. `%llm_config_persistent` - Activate the ambient magic field (where all cells become magical)
3. `%disable_llm_config_persistent` - Dispel the ambient magic field
4. `%%llm` - Cast a directed spell to the LLM wizard
5. `%%py` - Execute mundane Python code (when ambient magic is active)

## ✨ The Complete Spell Compendium

### 1. `%llm_config` - The Configuration Spell

This versatile spell allows you to adjust your magical settings and manage your resources.

```ipython
%llm_config [magical_parameters]
```

#### 🔮 Magical Parameters

| Arcane Parameter | What It Does |
|------------------|--------------|
| `-p`, `--persona` | Transform the AI into a different magical identity |
| `--show-persona` | Reveal the current persona's true nature |
| `--list-personas` | Summon a list of all available personas |
| `--set-override KEY VALUE` | Apply a magical override to a parameter (e.g., `--set-override temperature 0.5`) |
| `--remove-override KEY` | Remove a specific magical override |
| `--clear-overrides` | Dispel all magical overrides |
| `--show-overrides` | Reveal all active magical overrides |
| `--clear-history` | Erase your conversation history from memory (but keep system prompt) |
| `--show-history` | Unfold the scroll of your conversation history |
| `--save [FILENAME]` | Preserve your magical session in a scroll for later use |
| `--load SESSION_ID` | Recall a previously preserved magical session |
| `--list-sessions` | Reveal all preserved magical sessions |
| `--auto-save` | Enable automatic preservation of your magical conversations |
| `--no-auto-save` | Disable automatic preservation |
| `--list-snippets` | Reveal all available magical text fragments |
| `--snippet NAME` | Incorporate a magical text fragment into your next spell |
| `--sys-snippet NAME` | Add a system-level magical fragment to your next spell |
| `--status` | Reveal your current magical status and power levels |
| `--model NAME` | Change which magical entity you're communicating with |
| `--adapter {direct,langchain}` | Switch to a different magical communication method |
| `--list-mappings` | Show your magical name translations |
| `--add-mapping ALIAS FULL_NAME` | Create a new magical name shortcut |
| `--remove-mapping ALIAS` | Remove a magical name shortcut |

#### 📖 Spell Examples

```ipython
# Discover your magical name shortcuts
%llm_config --list-mappings

# Create a magical shortcut
%llm_config --add-mapping g4o gpt-4o

# Remove a magical shortcut
%llm_config --remove-mapping g4o

# Summon the Python expert persona
%llm_config --persona python_expert

# Communicate with a specific magical entity
%llm_config --model gpt-4o

# Adjust your spell's creativity
%llm_config --set-override temperature 0.7

# Include a magical scroll in your next communication
%llm_config --snippet code_context.py

# Check your magical status
%llm_config --status

# Switch to a different magical communication method
%llm_config --adapter langchain
```

### 2. `%llm_config_persistent` - The Ambient Magic Spell

This powerful enchantment has the same abilities as `%llm_config` but also creates a magical field around your notebook, turning every cell into a direct communication with the AI wizard.

```ipython
%llm_config_persistent [magical_parameters]
```

When the ambient magic field is active, any scroll (cell) you activate that doesn't start with a magical rune (`%` or `%%`) or command rune (`!`) will be sent as a message to the AI wizard, and their response will appear below.

#### 🔮 Magical Parameters

All the same magical parameters as `%llm_config` except for `--adapter`.

#### 📖 Spell Example

```ipython
# Create an ambient magic field with the coding assistant persona
%llm_config_persistent --persona coding_assistant --model gpt-4o
```

After casting this spell, you can simply write a question in any cell (no `%%llm` needed) and run it to receive wisdom from the AI wizard!

### 3. `%disable_llm_config_persistent` - The Dispel Magic Spell

This counter-spell removes the ambient magic field, returning your notebook to its normal state.

```ipython
%disable_llm_config_persistent
```

### 4. `%%llm` - The Direct Communication Spell

This cell magic allows you to send a specific message directly to the AI wizard.

```ipython
%%llm [magical_parameters]
Your message to the magical AI...
```

#### 🔮 Magical Parameters

| Arcane Parameter | What It Does |
|------------------|--------------|
| `-p`, `--persona` | Temporarily summon a different magical identity |
| `-m`, `--model` | Temporarily communicate with a different magical entity |
| `-t`, `--temperature` | Adjust the creativity of THIS spell only |
| `--max-tokens` | Limit the length of the magical response |
| `--no-history` | Cast a spell that leaves no trace in your history |
| `--no-stream` | Receive the complete magical response at once (no gradual appearance) |
| `--no-rollback` | Prevent automatic spell recovery if something goes wrong |
| `--param KEY VALUE` | Set any other magical parameter for this spell only |
| `--list-snippets` | Reveal all available magical fragments |
| `--snippet NAME` | Include a magical fragment in this spell |
| `--sys-snippet NAME` | Include a system-level magical fragment in this spell |

#### 📖 Spell Examples

```ipython
%%llm --persona data_alchemist --model gpt-4o
Transform this dataset into golden insights about customer behavior.
```

```ipython
%%llm -t 0.9 --param top_p 0.95
Craft a magical tale about a programmer who discovers an ancient spell book
containing Python code that can alter reality.
```

### 5. `%%py` - The Mundane Code Spell

When the ambient magic field is active, this spell allows you to execute regular Python code without magical interpretation.

```ipython
%%py
# This scroll contains regular Python incantations
fibonacci_spell = lambda n: n if n <= 1 else fibonacci_spell(n-1) + fibonacci_spell(n-2)
print(f"The 10th number in the sequence is {fibonacci_spell(10)}")
```

## 🌟 The Ambient Magic Field

The ambient magic field is a powerful enchantment that, when activated, allows any regular cell to be automatically processed as a communication with the AI wizard. This eliminates the need to mark each message with the `%%llm` rune.

- To create the field: `%llm_config_persistent`
- To dispel the field: `%disable_llm_config_persistent`

When the ambient magic field is active, cells that start with magical runes (`%`, `%%`) or command runes (`!`) still function normally, but all other cells become direct communications with the AI wizard.

If you need to cast regular Python spells while the ambient field is active, use the `%%py` magic rune.

> **⚠️ Warning:** The ambient magic field may sometimes intercept Jupyter's internal background functions like `__jupyter_exec_background__()` which are used for autocomplete and other IDE features. If your magical workspace begins acting strangely (such as code completion not working properly or internal Jupyter commands being sent to the AI wizard as messages), dispel the ambient magic using `%disable_llm_config_persistent` and use explicit `%%llm` runes instead.

## 📊 Magical Status Indicators

After each successful communication with the AI wizard (via `%%llm` or ambient magic), a status bar displays:

- Success rune (✅)
- Duration of the magical communication (⏱️)
- Token counts (magical energy consumed/received) (📥/📤)
- Estimated cost in magical currency (🪙)
- Which magical entity responded

This information helps you track your magical energy usage and costs.
