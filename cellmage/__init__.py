__version__ = '0.1.0'

# Configure logging as early as possible
from .utils.logging import setup_logging
setup_logging()

# Expose key classes and exceptions for easier import by users
from .chat_manager import ChatManager
from .exceptions import (
    NotebookLLMError,
    ConfigurationError,
    ResourceNotFoundError,
    LLMInteractionError,
    HistoryManagementError,
    PersistenceError,
    SnippetError
)
# Expose interfaces if they are intended for external implementation/type hinting
from .interfaces import (
    LLMClientInterface,
    PersonaLoader,
    SnippetProvider,
    HistoryStore,
    ContextProvider,
    StreamCallbackHandler
)
# Expose core models
from .models import Message, PersonaConfig, ConversationMetadata

# --- Optional: Provide a default factory function ---
# This simplifies setup for basic use cases

_default_manager_instance = None

def get_default_manager():
    """
    Gets or creates a default ChatManager instance with standard file-based components.
    Requires IPython for default context provider.
    """
    global _default_manager_instance
    if _default_manager_instance is None:
        try:
            # Import components needed for the default setup
            from .config import settings
            from .adapters.llm_client import LiteLLMAdapter
            from .resources.file_loader import FileLoader
            from .storage.markdown_store import MarkdownStore
            try:
                 from .integrations.ipython_magic import IPythonContextProvider
                 context_provider = IPythonContextProvider()
            except ImportError:
                 # IPython not available, use None for context
                 context_provider = None

            loader = FileLoader(settings.personas_dir, settings.snippets_dir)
            store = MarkdownStore(settings.save_dir)
            client = LiteLLMAdapter()

            _default_manager_instance = ChatManager(
                settings=settings,
                llm_client=client,
                persona_loader=loader,
                snippet_provider=loader,
                history_store=store,
                context_provider=context_provider
            )
        except Exception as e:
             # Log or raise a more specific setup error
             raise NotebookLLMError(f"Failed to create default ChatManager: {e}") from e
    return _default_manager_instance

__all__ = [
    "ChatManager",
    "get_default_manager",
    # Exceptions
    "NotebookLLMError",
    "ConfigurationError",
    "ResourceNotFoundError",
    "LLMInteractionError",
    "HistoryManagementError",
    "PersistenceError",
    "SnippetError",
    # Interfaces
    "LLMClientInterface",
    "PersonaLoader",
    "SnippetProvider",
    "HistoryStore",
    "ContextProvider",
    "StreamCallbackHandler",
    # Models
    "Message",
    "PersonaConfig",
    "ConversationMetadata",
    # Version
    "__version__",
]
