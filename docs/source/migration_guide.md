# Migration Guide: Moving to Unified Architecture

## Overview

CellMage has recently undergone a significant architectural improvement, unifying the previously separate `ChatManager` and `ConversationManager` classes into a single coherent system. This guide helps you migrate your code to use the new unified architecture.

## Why We Made This Change

The previous architecture had two overlapping components:

1. `ChatManager`: Handled LLM interactions, personas, and token tracking
2. `ConversationManager`: Handled conversation storage and management

This separation led to duplication, inconsistent APIs, and confusion about which component to use for what purpose. The unified architecture resolves these issues by providing a single point of entry for all conversation functionality.

## Benefits of the Unified Architecture

- **Single Source of Truth**: One class (`ConversationManager`) now manages all conversation state
- **Simplified Codebase**: Eliminated duplicate functionality and redundant code
- **Better Storage**: SQLite-based storage is now fully integrated with LLM capabilities
- **Improved API**: Cleaner, more consistent interfaces for developers
- **Future Extensibility**: The unified architecture will be easier to extend and maintain

## Deprecated Components

The following components are now deprecated and will be removed in a future version:

- `ChatManager` - Use `ConversationManager` instead
- `HistoryManager` - Functionality moved to `ConversationManager`

These components are maintained only for backward compatibility and will emit deprecation warnings when used.

## Migration Steps

### If you were using ChatManager:

```python
# Old code
from cellmage import ChatManager
from cellmage.context_providers.ipython_context_provider import get_ipython_context_provider

context_provider = get_ipython_context_provider()
manager = ChatManager(context_provider=context_provider)
response = manager.chat("Hello, how are you?")
```

```python
# New code
from cellmage import ConversationManager
from cellmage.context_providers.ipython_context_provider import get_ipython_context_provider

context_provider = get_ipython_context_provider()
manager = ConversationManager(context_provider=context_provider)
response = manager.chat("Hello, how are you?")
```

### If you were using HistoryManager:

```python
# Old code
from cellmage.history_manager import HistoryManager
history = HistoryManager()
history.add_message(message)
```

```python
# New code
from cellmage import ConversationManager
manager = ConversationManager()
manager.add_message(message)
```

### Use the factory functions:

The recommended way to get a fully configured manager is to use the factory function:

```python
from cellmage import get_default_conversation_manager

# Get a fully configured ConversationManager with all components
manager = get_default_conversation_manager()
```

## Method Mapping

### ChatManager to ConversationManager

| Old (ChatManager)     | New (ConversationManager)    | Notes                     |
|-----------------------|-----------------------------|---------------------------|
| `chat()`              | `chat()`                    | Same API                  |
| `get_history()`       | `get_messages()`            | Renamed for clarity       |
| `clear_history()`     | `clear_messages()`          | Renamed for clarity       |
| `save_conversation()` | `save_conversation()`       | Same API                  |
| `load_conversation()` | `load_conversation()`       | Same API                  |
| `set_override()`      | `set_override()`            | Same API                  |
| `get_overrides()`     | `get_overrides()`           | Same API                  |

### HistoryManager to ConversationManager

| Old (HistoryManager)  | New (ConversationManager)    | Notes                     |
|-----------------------|-----------------------------|---------------------------|
| `add_message()`       | `add_message()`             | Same API                  |
| `get_history()`       | `get_messages()`            | Renamed for clarity       |
| `clear_history()`     | `clear_messages()`          | Renamed for clarity       |
| `perform_rollback()`  | `perform_rollback()`        | Same API                  |
| `save_conversation()` | `save_conversation()`       | Same API                  |
| `load_conversation()` | `load_conversation()`       | Same API                  |

## SQLite Storage

The unified architecture makes SQLite the default storage backend. If you need to use another storage backend:

```python
# Memory storage
manager = ConversationManager(storage_type="memory")

# File-based storage  
manager = ConversationManager(storage_type="markdown")
```

## Questions?

If you have any questions about migrating to the new architecture, please [open an issue](https://github.com/yourusername/cellmage/issues) on our GitHub repository.