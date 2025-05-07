# 💾 Managing Conversations: Saving, Loading, and Searching Your LLM Chats

One of CellMage's most powerful features is its ability to save, load, and search your LLM conversations. This tutorial will guide you through managing your conversation history effectively.

## 📊 Understanding Conversation Storage

CellMage offers two primary storage backends:

1. **SQLite Storage** (default): Fast, searchable database storage
2. **Markdown Storage**: Human-readable file-based storage

Let's explore both options and see how to manage your conversations.

## 🔄 Basic Conversation Management

### Viewing Your Current Conversation

To see what's in your current conversation:

```python
# Show the full conversation history
%llm_config --show-history
```

This displays all messages in the current session, including:
- System messages (from personas)
- User messages (your prompts)
- Assistant messages (LLM responses)
- Metadata like timestamps and token counts

### Clearing History

To start fresh without any previous context:

```python
# Clear the conversation history but keep the system prompt
%llm_config --clear-history

# For a completely fresh start, also reset the persona
%llm_config --clear-history --persona default
```

## 💽 Saving Conversations

### Quick Save

The simplest way to save your current conversation:

```python
# Save with an automatically generated name
%llm_config --save
```

This creates a conversation named with a timestamp and the first few words of your conversation.

### Named Save

For better organization, name your conversations:

```python
# Save with a descriptive name
%llm_config --save "data_analysis_project"
```

The full name will include your provided name plus a timestamp: `data_analysis_project_20250507_...`

### Auto-Save

CellMage can automatically save your conversations:

```python
# Enable auto-saving
%llm_config --auto-save

# Disable auto-saving
%llm_config --no-auto-save
```

When auto-save is enabled, your conversation is saved after each interaction.

## 📂 Loading Conversations

### Listing Saved Conversations

To see what conversations you've saved:

```python
# List all saved conversations
%llm_config --list-sessions
```

This shows all your saved conversations with their IDs, names, and timestamps.

### Loading a Specific Conversation

To load a previously saved conversation:

```python
# Load by full ID
%llm_config --load "data_analysis_project_20250507_123456"

# You can also use just enough of the ID to be unique
%llm_config --load "data_analysis_project"
```

The loaded conversation replaces your current conversation history.

## 🔍 Searching Your Conversations with SQLite

SQLite storage (the default) provides powerful search capabilities:

```python
# First, load the SQLite extension
%load_ext cellmage.integrations.sqlite_magic

# Search for conversations containing specific text
%sqlite --search "machine learning"

# Show detailed statistics about your conversations
%sqlite --stats
```

### Advanced SQLite Operations

The `%sqlite` magic command offers many useful features:

```python
# View the status of your storage
%sqlite --status

# Create a new conversation
%sqlite --new

# Tag a conversation for better organization
%sqlite --tag current "project_x"

# Find all conversations with a specific tag
%sqlite --search-tag "project_x"

# Export a conversation to Markdown
%sqlite --export "~/exports/my_conversation.md"

# Import a conversation from Markdown
%sqlite --import-md "~/exports/my_conversation.md"
```

## 📄 Using Markdown Storage

If you prefer file-based storage instead of SQLite:

```python
# Configure CellMage to use Markdown storage
%llm_config --set-override storage_type file
```

Markdown storage saves each conversation as a separate `.md` file in your `llm_conversations` directory (by default). These files:
- Are human-readable
- Can be version-controlled
- Include all conversation messages and metadata
- Can be imported back into CellMage

## 🗂️ Best Practices for Conversation Management

1. **Use descriptive names** when saving conversations to find them easily later
2. **Add tags** to group related conversations (e.g., "project_x", "research", "debugging")
3. **Export important conversations** as backups or for sharing with others
4. **Clear history** when switching to a new topic to avoid context confusion
5. **Use SQLite storage** for larger projects with many conversations
6. **Use Markdown storage** when you want to read or edit conversations outside of CellMage

## 🔄 Managing Multiple Projects

For different projects, you can use separate conversation stores:

```python
# Set a custom SQLite database path
%llm_config --set-override sqlite_path ~/projects/project_a/conversations.db
```

This allows you to maintain separate conversation histories for different projects.

## 🚀 Next Steps

Now that you know how to manage your conversations, you might want to explore:
- [Creating Custom Personas](working_with_personas.md) to shape LLM behavior
- [Using Snippets](using_snippets.md) to provide reusable context
- [Advanced Configuration](../configuration.md) for customizing CellMage
