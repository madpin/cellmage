# SQLite Storage

The CellMage library provides a powerful SQLite-based storage system for managing LLM conversations. This storage system offers enhanced capabilities over the default storage approach, including:

- **Improved Search**: Full-text search across all conversations
- **Tag Support**: Add custom tags to conversations for better organization
- **Metadata**: Store and retrieve detailed metadata about conversations
- **Statistics**: Generate usage statistics and analytics
- **Export/Import**: Export conversations to Markdown and import them back

## Quick Start

To use SQLite storage in your Jupyter notebook:

```python
# Load the SQLite magic extension
%load_ext cellmage.integrations.sqlite_magic

# Show storage statistics and status
%sqlite --stats --status

# Create a new conversation
%sqlite --new

# Add tags to the current conversation
%sqlite --tag current "important"
```

## Sending Prompts with SQLite Storage

Use the `%%sqlite_llm` cell magic to send prompts to the LLM while storing history in SQLite:

```text
%%sqlite_llm
What is the capital of France?
```

The SQLite storage will automatically manage conversation context, handle cell re-execution, and save all conversation history.

## SQLite Magic Commands

The `%sqlite` line magic provides these options:

| Option | Description |
|--------|-------------|
| `--status` | Show current SQLite storage status |
| `--stats` | Show statistics about stored conversations |
| `--list` | List all stored conversations |
| `--new` | Start a new conversation |
| `--load ID` | Load a specific conversation by ID |
| `--delete ID` | Delete a conversation by ID |
| `--tag ID TAG` | Add a tag to a conversation |
| `--search QUERY` | Search conversations by content |
| `--export PATH` | Export conversation to a markdown file |
| `--import-md PATH` | Import a markdown conversation file |

## Programmatic Usage

You can also use the SQLite storage system programmatically:

```python
from cellmage import ConversationManager, Message

# Create a conversation manager with SQLite storage
manager = ConversationManager()

# Add messages
manager.add_message(Message(role="user", content="Hello, how are you?"))

# Save conversation (automatic when adding messages)
# The current conversation ID is available at manager.current_conversation_id

# Create a new conversation
new_id = manager.create_new_conversation()

# Load a conversation
manager.load_conversation("conversation_id_here")

# Search conversations
from cellmage.storage.sqlite_store import SQLiteStore
store = SQLiteStore()
results = store.search_conversations("search term")
```

## Migration from File-based Storage

If you have existing conversations stored in files, you can migrate them to SQLite:

```python
from cellmage import get_default_manager
from cellmage.magic_commands.persistence import migrate_to_sqlite

# Get your current chat manager
chat_manager = get_default_manager()

# Migrate to SQLite
conversation_manager = migrate_to_sqlite(chat_manager)
```

## Benefits of SQLite Storage

- **Performance**: Faster retrieval for large conversation histories
- **Reliability**: Robust storage with proper transaction handling
- **Search**: Fast full-text search across all conversations
- **Organization**: Tag support for better conversation management
- **Portability**: Single file database that's easy to backup

## Architecture

The SQLite storage implementation consists of these components:

1. `SQLiteStore`: Core storage implementation in `storage/sqlite_store.py`
2. `ConversationManager`: High-level interface in `conversation_manager.py`
3. `sqlite_magic.py`: IPython integration
4. Magic command modules in `magic_commands/` directory