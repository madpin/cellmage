# 🧠 Core Concepts

## 🪄 The CellMage Philosophy

CellMage is built around the idea that LLMs should integrate seamlessly into your workflow, not the other way around. Our design philosophy centers on:

1. **Minimal Friction**: No need for complex setup or context switching
2. **Maximum Control**: Fine-grained control over model behavior and context
3. **Intuitive Magic**: Commands that feel natural and are easy to remember
4. **Persistent Memory**: Your conversations saved and retrievable
5. **Extensible Platform**: Connect to other tools and services you already use

## 📚 Key Components

### 🔮 Magic Commands

CellMage provides two main types of magic commands:

- **Line Magic** (`%command`): Single-line commands that configure behavior or trigger specific actions
- **Cell Magic** (`%%command`): Transforms the entire cell into a prompt for the LLM

Learn more in [IPython Magic Commands](./ipython_magic_commands.md).

## 🏗️ Internal Architecture

Understanding CellMage's internal architecture will help you make the most of its capabilities and extend it to suit your needs.

### 🧠 ChatManager

The ChatManager is the central orchestrator of CellMage. It coordinates all other components and manages the flow of information between them.

```python
# The ChatManager ties together all core components
chat_manager = ChatManager(
    settings=settings,
    llm_client=llm_client,         # Adapter for LLM communication
    persona_loader=loader,         # For loading personas
    snippet_provider=loader,       # For loading snippets
    history_store=store,           # For conversation persistence
    context_provider=context_provider  # For notebook integration
)
```

Key responsibilities:
- Handling user prompts and generating responses from LLMs
- Managing the current persona and its settings
- Coordinating conversation history and persistence
- Applying runtime parameter overrides
- Tracking token usage and costs

Located in: `cellmage/chat_manager.py`

### 📜 ConversationManager & HistoryManager

CellMage uses two main components to manage conversations:

**ConversationManager** focuses on the storage and persistence of conversations:
- Creating new conversations
- Saving and loading conversations
- Managing conversation metadata
- Handling search and retrieval

```python
# ConversationManager wraps the storage mechanism
conversation_manager = ConversationManager(
    db_path="~/.cellmage/conversations.db",  # Where to store data
    storage_type="sqlite"                    # Which storage backend to use
)
```

Located in: `cellmage/conversation_manager.py`

**HistoryManager** focuses on the in-memory manipulation of the current conversation:
- Adding messages to the current conversation
- Clearing or rolling back the conversation
- Managing the conversation context window
- Handling auto-save functionality

```python
# HistoryManager manages the current conversation
history_manager = HistoryManager(
    conversation_store=store,   # Where to persist history
    auto_save=True              # Whether to save automatically
)
```

Located in: `cellmage/history_manager.py`

### 🎭 Personas

Personas define how the LLM behaves. Each persona includes:

- A system prompt that guides the LLM's responses
- Default parameter settings (model, temperature, etc.)
- Optional metadata like name and description

**Creating Personas**

Personas are stored as Markdown files with YAML frontmatter in the `llm_personas` directory. For example:

```markdown
---
name: Code Reviewer
model: gpt-4o
temperature: 0.3
description: A careful code reviewer that offers constructive feedback
---
You are an expert code reviewer with experience across multiple programming languages.
Analyze code for bugs, security issues, performance problems, and style inconsistencies.
Always be constructive in your feedback and explain the reasoning behind your suggestions.
Offer examples of better implementations when appropriate.
```

**Loading Personas**

The `FileLoader` class handles loading personas from disk:

```python
from cellmage.resources.file_loader import FileLoader

# Initialize loader with directories to search
loader = FileLoader(
    personas_dir="./llm_personas",
    snippets_dir="./llm_snippets"
)

# Load a specific persona
persona = loader.get_persona("code_reviewer")
```

Located in: `cellmage/resources/file_loader.py`

### 📋 Snippets

Snippets are reusable pieces of context that you can inject into your prompts. Unlike personas, which define the LLM's behavior, snippets provide context that the LLM can reference.

**Creating Snippets**

Snippets are simple text files stored in the `llm_snippets` directory:

```python
# sample_code.py in llm_snippets directory
def calculate_metrics(data):
    """
    Calculate key metrics for the given dataset.
    """
    return {
        "mean": sum(data) / len(data),
        "median": sorted(data)[len(data) // 2],
        "max": max(data),
        "min": min(data)
    }
```

**Using Snippets**

Snippets are loaded using the same `FileLoader` class as personas:

```python
# Load a snippet
snippet_content = loader.get_snippet("sample_code.py")
```

Snippets can be:
- Added as user messages (default)
- Added as system messages (using `--sys-snippet`)
- Applied globally or just for a single cell

Located in: `cellmage/resources/file_loader.py`

### 🔌 Adapters

CellMage uses adapters to communicate with different LLM providers. This abstraction allows CellMage to work with various LLM backends without changing its core functionality.

**DirectLLMAdapter**

The DirectLLMAdapter communicates directly with OpenAI-compatible APIs:
- Makes direct HTTP requests to the LLM provider's API
- Handles streaming responses
- Manages request parameters and error handling
- Works with both OpenAI API and compatible endpoints

```python
from cellmage.adapters.direct_client import DirectLLMAdapter

# Initialize the adapter
client = DirectLLMAdapter(
    api_key="your-api-key",
    api_base="https://api.openai.com/v1",
    default_model="gpt-4o"
)

# Send a message
response = client.send_message([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Tell me about CellMage."}
])
```

Located in: `cellmage/adapters/direct_client.py`

**LangChainAdapter**

The LangChainAdapter uses LangChain for more advanced capabilities:
- Integrates with the LangChain ecosystem
- Supports memory, prompts, and chains
- Enables more complex workflows
- Provides access to additional models through LangChain

```python
from cellmage.adapters.langchain_client import LangChainAdapter

# Initialize the adapter
client = LangChainAdapter(
    api_key="your-api-key",
    default_model="gpt-3.5-turbo"
)

# Using LangChain features through the adapter
response = client.send_message(messages, temperature=0.7)
```

Located in: `cellmage/adapters/langchain_client.py`

### 💾 Storage Backends

CellMage offers multiple options for persisting conversations:

**SQLiteStore** (default)
- Fast, efficient SQL-based storage
- Support for tagging, searching, and statistics
- Reliable transaction-based operations
- Perfect for larger conversation histories

```python
from cellmage.storage.sqlite_store import SQLiteStore

# Initialize the store
store = SQLiteStore(db_path="~/.cellmage/conversations.db")

# Store a conversation
store.save_conversation(conversation_id, messages, metadata)

# Search conversations
results = store.search_conversations("machine learning")

# Add tags
store.add_tag(conversation_id, "important")
```

Located in: `cellmage/storage/sqlite_store.py`

**MarkdownStore** (legacy)
- Simple file-based storage using Markdown files
- Human-readable format
- Easy to version control
- Good for simple use cases

```python
from cellmage.storage.markdown_store import MarkdownStore

# Initialize the store
store = MarkdownStore(base_dir="./llm_conversations")

# Operations are similar to SQLiteStore
```

Located in: `cellmage/storage/markdown_store.py`

**MemoryStore**
- In-memory storage for temporary use cases
- No persistence between sessions
- Useful for testing or ephemeral usage

```python
from cellmage.storage.memory_store import MemoryStore

# Initialize the store
store = MemoryStore()
```

Located in: `cellmage/storage/memory_store.py`

### 🏷️ Model Mapping

CellMage supports model aliasing to create shortcuts for model names. This allows you to use shorter, more memorable names instead of the full model identifiers.

**Model Mapping Configuration**

Model aliases are defined in a `cellmage_models.yml` file:

```yaml
# Example cellmage_models.yml
mappings:
  g4: gpt-4o
  g4m: gpt-4o-mini
  g3: gpt-3.5-turbo
  claud3h: claude-3-haiku
  claud3s: claude-3-sonnet
  claud3o: claude-3-opus
```

CellMage looks for this file in your working directory. A reference example is provided in `cellmage/examples/cellmage_models.yml`.

**Using Model Aliases**

Once defined, you can use your aliases with any model parameter:

```python
# Using an alias
%llm_config --model g4m

# Same as
%llm_config --model gpt-4o-mini
```

Located in: `cellmage/model_mapping.py`

## 🧩 How It All Fits Together

1. **Configuration** sets up your environment (via `%llm_config` or environment variables)
2. **Magic Commands** provide the interface to CellMage
3. **Personas and Snippets** shape the context and behavior of the LLM
4. **ChatManager** orchestrates the conversation flow
5. **Adapters** handle communication with LLM providers
6. **ConversationManager** and **HistoryManager** track and persist conversations
7. **Storage Backends** save your conversations for future reference
8. **Integrations** bring external context into your workflow

This modular architecture makes CellMage both powerful and flexible, allowing you to customize your experience while maintaining simplicity.

## 📊 Component Interactions

Here's a diagram of how the components interact:

```
+------------------+      +-------------------+      +---------------+
|                  |      |                   |      |               |
| Magic Commands   +----->+  ChatManager      +----->+  LLM Adapters |
|                  |      |                   |      |               |
+------------------+      +-------------------+      +---------------+
        ^                         |                         |
        |                         v                         v
+------------------+      +-------------------+      +---------------+
|                  |      |                   |      |               |
| Integrations     |      | HistoryManager    |      |  API Services |
|                  |      | ConversationMgr   |      |               |
+------------------+      +-------------------+      +---------------+
        ^                         |
        |                         v
+------------------+      +-------------------+
|                  |      |                   |
| Resources        |      | Storage Backends  |
| (Personas,       |      | (SQLite,          |
|  Snippets)       |      |  Markdown)        |
+------------------+      +-------------------+
```

When you run a magic command:
1. The command is processed by the appropriate magic class
2. The ChatManager is called to handle the request
3. PersonaLoader and SnippetProvider are used to shape the context
4. The LLM adapter sends the request to the model
5. The response is added to history and displayed
6. The ConversationManager persists the conversation via the storage backend
