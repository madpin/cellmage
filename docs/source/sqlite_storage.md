# 📚 The Magical Memory Vault: SQLite Storage

CellMage provides a powerful SQLite-based storage system - think of it as your magical memory vault where all your conversations with the AI wizard are preserved with perfect clarity! This enchanted storage offers:

- 🔍 **Crystal Ball Search**: Find any past conversation with full-text search
- 🏷️ **Magic Tags**: Label and organize your conversations with custom tags
- 📊 **Wizard Analytics**: Track your LLM usage with detailed statistics
- 📝 **Spell Archives**: Export conversations to Markdown scrolls (and import them back)

## 🪄 Quick Start

To begin using the magical SQLite storage:

```python
# Load the extension with the SQLite vault
%load_ext cellmage.integrations.sqlite_magic

# Check the status of your storage vault
%sqlite --status
```

## 💬 Casting Spells with SQLite Storage

The SQLite storage automatically captures all your magical conversations. Use it just like regular CellMage:

```python
# Cast a spell (sends to LLM and stores in SQLite)
%%llm
Explain how wizards might use databases in magical societies.
```

## 🧙‍♂️ SQLite Magic Commands

The `%sqlite` line magic gives you special powers:

| Magical Command | What It Does |
|-----------------|--------------|
| `--status` | Reveals the current state of your memory vault |
| `--stats` | Shows statistics about your stored conversations |
| `--list` | Unrolls a scroll listing all stored conversations |
| `--new` | Begins a fresh conversation in a new vault |
| `--load ID` | Retrieves a specific conversation by ID |
| `--delete ID` | Banishes a conversation from the vault |
| `--tag ID TAG` | Marks a conversation with a magical tag |
| `--search QUERY` | Searches for specific words in your conversations |
| `--export PATH` | Transforms a conversation into a markdown scroll |
| `--import-md PATH` | Absorbs a markdown scroll into your vault |

## 📜 Examples of Magical Storage

```python
# Start a new conversation
%sqlite --new

# Tag your current conversation as "potions"
%sqlite --tag current potions

# Search for conversations about "dragons"
%sqlite --search dragons

# Export your current conversation to share with other wizards
%sqlite --export ~/my_dragon_research.md

# Load a specific conversation by ID
%sqlite --load 42
```

## 🧪 Programmatic Alchemy

For advanced wizards who wish to control the storage vault directly:

```python
from cellmage.storage.sqlite_store import SQLiteStore

# Create a custom storage vault
store = SQLiteStore(db_path="~/.cellmage/my_special_vault.db")

# Store a magical conversation
conversation_id = store.save_conversation(
    messages=[{"role": "user", "content": "What is magic?"}],
    metadata={"tags": ["philosophy", "beginners"]}
)

# Retrieve conversations with specific tags
philosophical_convos = store.get_conversations_with_tag("philosophy")
```

## 🧭 Migrating from Scroll-based Storage

If you have old conversations stored in markdown files:

```text
# Import a specific markdown conversation
%sqlite --import-md path/to/conversation.md

# Or import all conversations from a directory
import glob
from pathlib import Path

for file_path in glob.glob("path/to/conversations/*.md"):
    !ipython -c "%sqlite --import-md {file_path}"
```

## ✨ Benefits of the Magical Vault

- **⚡ Speed**: Access conversations instantly, even when you have thousands
- **🛡️ Security**: Your conversations are safely locked in a single file
- **🔍 Discovery**: Easily find past conversations when you need them
- **📊 Insights**: Track how you use your magical powers over time

## 🏰 Vault Architecture

The magic behind the vault consists of these components:

1. `SQLiteStore`: The core enchantment in `storage/sqlite_store.py`
2. `ConversationManager`: The high wizard interface in `conversation_manager.py`
3. `sqlite_magic.py`: The magical bridge to IPython
4. Magic command modules in the `magic_commands/` chamber
