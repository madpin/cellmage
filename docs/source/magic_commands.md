# 🧙 The Spell Book: CellMage Magic Commands

Welcome to the official spell book of CellMage! Here you'll find all the magical incantations (IPython magic commands) that allow you to summon the power of Large Language Models directly within your enchanted notebooks. Master these spells to become a true wizard of AI!

## 📜 Summoning the Magic

Before casting any spells, you must first invite the magical presence into your notebook:

```ipython
%load_ext cellmage
```

## 🪄 Your Magical Arsenal

The CellMage grimoire contains these powerful core spells:

1. `%llm_config` - Configure your magical powers and manage your arcane resources
2. `%llm_config_persistent` - Activate the ambient magic field (where all cells become magical)
3. `%disable_llm_config_persistent` - Dispel the ambient magic field
4. `%%llm` - Cast a directed spell to the LLM wizard
5. `%%py` - Execute mundane Python code (when ambient magic is active)

And these integration enchantments:

6. `%confluence` - Summon knowledge from the Confluence realm
7. `%jira` - Call upon the wisdom of Jira issue trackers
8. `%github` - Channel the power of GitHub repositories
9. `%gitlab` - Draw upon the essence of GitLab projects
10. `%webcontent` - Extract magical insights from the web
11. `%gdocs` - Commune with the scrolls of Google Docs
12. `%sqlite` - Manage your spellbook archives
13. `%img` - Process and display images

## ✨ The Complete Spell Compendium

### 1. `%llm_config` - The Configuration Spell

This versatile spell allows you to adjust your magical settings and manage your resources.

```ipython
%llm_config [magical_parameters]
```

#### 🔮 Magical Parameters

| Arcane Parameter                | What It Does                                                                     |
| ------------------------------- | -------------------------------------------------------------------------------- |
| `-p`, `--persona`               | Transform the AI into a different magical identity                               |
| `--show-persona`                | Reveal the current persona's true nature                                         |
| `--list-personas`               | Summon a list of all available personas                                          |
| `--set-override KEY VALUE`      | Apply a magical override to a parameter (e.g., `--set-override temperature 0.5`) |
| `--remove-override KEY`         | Remove a specific magical override                                               |
| `--clear-overrides`             | Dispel all magical overrides                                                     |
| `--show-overrides`              | Reveal all active magical overrides                                              |
| `--clear-history`               | Erase your conversation history from memory (but keep system prompt)             |
| `--show-history`                | Unfold the scroll of your conversation history                                   |
| `--save [FILENAME]`             | Preserve your magical session in a scroll for later use                          |
| `--load SESSION_ID`             | Recall a previously preserved magical session                                    |
| `--list-sessions`               | Reveal all preserved magical sessions                                            |
| `--auto-save`                   | Enable automatic preservation of your magical conversations                      |
| `--no-auto-save`                | Disable automatic preservation                                                   |
| `--list-snippets`               | Reveal all available magical text fragments                                      |
| `--snippet NAME`                | Incorporate a magical text fragment into your next spell                         |
| `--sys-snippet NAME`            | Add a system-level magical fragment to your next spell                           |
| `--status`                      | Reveal your current magical status and power levels                              |
| `--model NAME`                  | Change which magical entity you're communicating with                            |
| `--adapter {direct,langchain}`  | Switch to a different magical communication method                               |
| `--list-mappings`               | Show your magical name translations                                              |
| `--add-mapping ALIAS FULL_NAME` | Create a new magical name shortcut                                               |
| `--remove-mapping ALIAS`        | Remove a magical name shortcut                                                   |

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

| Arcane Parameter      | What It Does                                                          |
| --------------------- | --------------------------------------------------------------------- |
| `-p`, `--persona`     | Temporarily summon a different magical identity                       |
| `-m`, `--model`       | Temporarily communicate with a different magical entity               |
| `-t`, `--temperature` | Adjust the creativity of THIS spell only                              |
| `--max-tokens`        | Limit the length of the magical response                              |
| `--no-history`        | Cast a spell that leaves no trace in your history                     |
| `--no-stream`         | Receive the complete magical response at once (no gradual appearance) |
| `--no-rollback`       | Prevent automatic spell recovery if something goes wrong              |
| `--param KEY VALUE`   | Set any other magical parameter for this spell only                   |
| `--list-snippets`     | Reveal all available magical fragments                                |
| `--snippet NAME`      | Include a magical fragment in this spell                              |
| `--sys-snippet NAME`  | Include a system-level magical fragment in this spell                 |

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

### 6. `%confluence` - The Confluence Crystal Ball

This enchantment allows you to peer into the Confluence realm and retrieve knowledge stored there.

```ipython
%confluence [identifier] [magical_parameters]
```

#### 🔮 Magical Parameters

| Arcane Parameter | What It Does                                                    |
| ---------------- | --------------------------------------------------------------- |
| `identifier`     | Page identifier (SPACE:Title format or page ID)                 |
| `--cql QUERY`    | Confluence Query Language search query                          |
| `--max NUMBER`   | Maximum number of results for CQL queries (default: 5)          |
| `--system`       | Add content as a system message (rather than user)              |
| `--show`         | Display the content without adding to history                   |
| `--text`         | Use plain text format instead of Markdown (Markdown is default) |
| `--no-content`   | For CQL search, return only metadata without page content       |
| `--content`      | For CQL search, fetch full content of each page                 |

#### 📖 Spell Examples

```ipython
# Fetch a specific Confluence page
%confluence ENGINEERING:System Architecture

# Search Confluence with CQL
%confluence --cql "space = DEV AND title ~ 'API Documentation'"
```

### 7. `%jira` - The Issue Tracking Telescope

This spell allows you to inspect issues and tasks from the Jira realm.

```ipython
%jira [issue_key] [magical_parameters]
```

#### 🔮 Magical Parameters

| Arcane Parameter  | What It Does                                          |
| ----------------- | ----------------------------------------------------- |
| `issue_key`       | Jira issue key (e.g., PROJECT-123)                    |
| `--jql QUERY`     | JQL search query instead of a specific issue          |
| `--max NUMBER`    | Maximum number of results for JQL search (default: 5) |
| `--fields FIELDS` | Comma-separated list of fields to include             |
| `--comments`      | Include issue comments                                |
| `--system`        | Add as system message instead of user message         |
| `--show`          | Display content without adding to history             |
| `--text`          | Use plain text instead of Markdown format             |

#### 📖 Spell Examples

```ipython
# Fetch a specific Jira issue
%jira PROJ-123

# Search for issues with JQL
%jira --jql "project = BACKEND AND status = 'In Progress' AND assignee = currentUser()"
```

### 8. `%github` - The GitHub Repository Mirror

This enchantment allows you to peer into GitHub repositories and extract information.

```ipython
%github [repo/path] [magical_parameters]
```

#### 🔮 Magical Parameters

| Arcane Parameter | What It Does                                             |
| ---------------- | -------------------------------------------------------- |
| `repo_path`      | Repository owner/name or file path within a repository   |
| `--issue NUMBER` | Fetch a specific issue by number                         |
| `--pr NUMBER`    | Fetch a specific pull request by number                  |
| `--search QUERY` | Search for issues with the given query                   |
| `--max NUMBER`   | Maximum number of search results (default: 5)            |
| `--comments`     | Include comments on issues/PRs                           |
| `--system`       | Add as system message instead of user message            |
| `--show`         | Display content without adding to history                |
| `--branch NAME`  | Branch to use when fetching files (default: main/master) |

#### 📖 Spell Examples

```ipython
# View a specific file from a GitHub repo
%github facebook/react/README.md

# Get information about an issue
%github facebook/react --issue 42 --comments

# Search for issues
%github facebook/react --search "state management" --max 10
```

### 9. `%gitlab` - The GitLab Project Portal

This spell connects to GitLab projects and extracts information.

```ipython
%gitlab [repo/path] [magical_parameters]
```

#### 🔮 Magical Parameters

| Arcane Parameter | What It Does                                             |
| ---------------- | -------------------------------------------------------- |
| `repo_path`      | Project path or file path within a project               |
| `--issue NUMBER` | Fetch a specific issue by number                         |
| `--mr NUMBER`    | Fetch a specific merge request by number                 |
| `--search QUERY` | Search for issues with the given query                   |
| `--max NUMBER`   | Maximum number of search results (default: 5)            |
| `--comments`     | Include comments on issues/MRs                           |
| `--system`       | Add as system message instead of user message            |
| `--show`         | Display content without adding to history                |
| `--branch NAME`  | Branch to use when fetching files (default: main/master) |

#### 📖 Spell Examples

```ipython
# View a specific file from a GitLab project
%gitlab group/project/README.md

# Get information about an issue
%gitlab group/project --issue 42 --comments
```

### 10. `%webcontent` - The Web Divination Spell

This enchantment extracts content from webpages and prepares it for analysis.

```ipython
%webcontent [url] [magical_parameters]
```

#### 🔮 Magical Parameters

| Arcane Parameter    | What It Does                                                     |
| ------------------- | ---------------------------------------------------------------- |
| `url`               | URL of the webpage to fetch                                      |
| `--clean`           | Clean and extract main content (default behavior)                |
| `--raw`             | Get raw HTML content without cleaning                            |
| `--method METHOD`   | Content extraction method: trafilatura (default), bs4, or simple |
| `--system`          | Add as system message instead of user message                    |
| `--show`            | Display content without adding to history                        |
| `--include-images`  | Include image references in the output                           |
| `--no-links`        | Remove hyperlinks from the output                                |
| `--timeout SECONDS` | Request timeout in seconds (default: 30)                         |

#### 📖 Spell Examples

```ipython
# Get clean content from a webpage
%webcontent https://en.wikipedia.org/wiki/Artificial_intelligence

# Keep links and images in the output
%webcontent https://blog.example.com/tutorial --include-images
```

### 11. `%gdocs` - The Google Docs Summoning Spell

This enchantment allows you to access content from Google Docs and use it as context.

```ipython
%gdocs [document_id] [magical_parameters]
```

#### 🔮 Magical Parameters

| Arcane Parameter                     | What It Does                                                             |
| ------------------------------------ | ------------------------------------------------------------------------ |
| `document_id`                        | Google Document ID or URL                                                |
| `--system`                           | Add as system message instead of user message                            |
| `--show`                             | Display content without adding to history                                |
| `--search QUERY`                     | Search for Google Docs files containing the specified term               |
| `--content`                          | Retrieve and display content for search results                          |
| `--max-results NUMBER`               | Maximum number of search results to return (default: 10)                 |
| `--max-content NUMBER`               | Maximum number of documents to retrieve content for (default: 3)         |
| `--timeout SECONDS`                  | Request timeout in seconds (default: 300)                                |
| `--author EMAIL`                     | Filter documents by author/owner email (comma-separated for multiple)    |
| `--modified-after`, `--updated DATE` | Filter by modification date (YYYY-MM-DD or natural language)             |
| `--order-by FIELD`                   | How to order search results (relevance, modifiedTime, createdTime, name) |
| `--auth-type TYPE`                   | Authentication type to use (oauth or service_account)                    |

#### 📖 Spell Examples

```ipython
# Fetch a specific Google Document
%gdocs 1aBcDeFgHiJkLmNoPqRsTuVwXyZ

# Search for documents and retrieve content
%gdocs --search "project proposal" --content --max-content 5

# Search with filters
%gdocs --search "meeting notes" --author john@example.com,jane@example.com --updated "2 weeks" --timeout 600
```

### 12. `%sqlite` - The Memory Archive Spell

This enchantment manages your stored conversations with the magic realm.

```ipython
%sqlite [magical_parameters]
```

#### 🔮 Magical Parameters

| Arcane Parameter   | What It Does                                             |
| ------------------ | -------------------------------------------------------- |
| `--status`         | Show the current state of the SQLite storage             |
| `--stats`          | Display statistics about stored conversations            |
| `--list`           | List all stored conversations                            |
| `--new`            | Start a new conversation                                 |
| `--load ID`        | Load a specific conversation by ID                       |
| `--delete ID`      | Delete a conversation by ID                              |
| `--tag ID TAG`     | Add a tag to a conversation                              |
| `--search QUERY`   | Search for conversations with content matching the query |
| `--export PATH`    | Export a conversation to markdown file                   |
| `--import-md PATH` | Import a conversation from markdown file                 |

#### 📖 Spell Examples

```ipython
# Show all stored conversations
%sqlite --list

# Start a new conversation
%sqlite --new

# Load a previous conversation
%sqlite --load conversation_20250508_123456

# Search for conversations about a topic
%sqlite --search "neural networks"
```

### 13. `%img` - The Image Processing Portal

This spell allows you to process, display, and add images to your LLM conversations.

```ipython
%img path/to/image.jpg [magical_parameters]
```

#### 🔮 Magical Parameters

| Arcane Parameter          | What It Does                                                      |
| ------------------------- | ----------------------------------------------------------------- |
| `image_path`              | Path to the image file to process                                 |
| `-r`, `--resize` WIDTH    | Width to resize the image to while maintaining aspect ratio       |
| `-q`, `--quality` QUALITY | Quality for lossy image formats (0.0-1.0)                         |
| `--show`                  | Display the image inline after processing                         |
| `-i`, `--info`            | Display information about the image                               |
| `-a`, `--add-to-chat`     | Add the image to the current chat session (default: always added) |
| `-c`, `--convert`         | Force conversion to a compatible format                           |
| `-f`, `--format` FORMAT   | Format to convert the image to (e.g., "jpg", "png", "webp")       |

#### 📖 Spell Examples

```ipython
# Process an image and add it to conversation context (no display)
%img path/to/image.jpg

# Process, display, and show information about an image
%img path/to/image.jpg --show --info

# Resize an image to 800px width and display it
%img path/to/image.jpg --resize 800 --show

# Convert an image to a different format with quality adjustment
%img path/to/image.jpg --format webp --quality 0.85 --show
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

## 🧪 Example Magical Potions

Here are some example incantations to help you get started on your magical journey:

```ipython
# Load the magical extension
%load_ext cellmage

# Set the default model and persona
%llm_config --model gpt-4o --persona python_expert

# Ask a question with a specific model for this call only
%%llm -m gpt-4o
Explain the visitor pattern in software design

# Enable ambient mode with specific settings
%llm_config_persistent --model gpt-4o-mini --temperature 0.7

# Execute Python code in ambient mode
%%py
import pandas as pd
print(pd.__version__)

# Disable ambient mode
%disable_llm_config_persistent

# Load integration extensions as needed
%load_ext cellmage.magic_commands.tools.confluence_magic
%load_ext cellmage.magic_commands.tools.github_magic
%load_ext cellmage.magic_commands.tools.webcontent_magic

# Fetch content from various sources
%confluence TEAM:Project Overview
%github myorg/myrepo --issue 42
%webcontent https://example.com/article
```
