# Configure logging as early as possible
from .utils.logging import setup_logging

setup_logging()

# Import required Python libraries
import logging  # noqa: E402
import os  # noqa: E402

# Expose key classes and exceptions for easier import by users
from .chat_manager import ChatManager  # noqa: E402
from .exceptions import (  # noqa: E402
    ConfigurationError,
    HistoryManagementError,
    LLMInteractionError,
    NotebookLLMError,
    PersistenceError,
    ResourceNotFoundError,
    SnippetError,
)

# Expose interfaces if they are intended for external implementation/type hinting
from .interfaces import (  # noqa: E402
    ContextProvider,
    HistoryStore,
    LLMClientInterface,
    PersonaLoader,
    SnippetProvider,
    StreamCallbackHandler,
)

# Expose core models
from .models import ConversationMetadata, Message, PersonaConfig  # noqa: E402

# Import IPython extension entry points
try:
    from .integrations.ipython_magic import (
        load_ipython_extension,
        unload_ipython_extension,
    )

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

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

            # Import DirectLLMAdapter - no fallback to LiteLLMAdapter
            try:
                from .adapters.direct_client import DirectLLMAdapter

                adapter_class = DirectLLMAdapter
            except ImportError:
                raise ConfigurationError(
                    "DirectLLMAdapter is not available. Please check your installation."
                )

            from .resources.file_loader import MultiFileLoader
            from .storage.markdown_store import MarkdownStore

            try:
                from .context_providers.ipython_context_provider import (
                    IPythonContextProvider,
                )

                context_provider = IPythonContextProvider()
            except ImportError:
                # IPython not available, use None for context
                context_provider = None

            # Set up multiple folders for personas and snippets
            persona_dirs = settings.all_personas_dirs.copy()  # Start with configured dirs
            snippet_dirs = settings.all_snippets_dirs.copy()

            # Auto-detect additional directories
            # First check the root of the project
            root_snippets = "snippets"
            if os.path.isdir(root_snippets) and root_snippets not in snippet_dirs:
                snippet_dirs.append(root_snippets)

            # Check for notebook directories
            notebook_dir = os.path.abspath("notebooks")
            if os.path.isdir(notebook_dir):
                # Add notebook-specific directories
                for subdir_name in ["llm_personas", "personas"]:
                    notebooks_personas_dir = os.path.join(notebook_dir, subdir_name)
                    if (
                        os.path.isdir(notebooks_personas_dir)
                        and notebooks_personas_dir not in persona_dirs
                    ):
                        persona_dirs.append(notebooks_personas_dir)

                for subdir_name in ["llm_snippets", "snippets"]:
                    notebooks_snippets_dir = os.path.join(notebook_dir, subdir_name)
                    if (
                        os.path.isdir(notebooks_snippets_dir)
                        and notebooks_snippets_dir not in snippet_dirs
                    ):
                        snippet_dirs.append(notebooks_snippets_dir)

                # Check subdirectories: examples, tests, tutorials
                for folder in ["examples", "tests", "tutorials"]:
                    sub_dir = os.path.join(notebook_dir, folder)
                    if os.path.isdir(sub_dir):
                        # Check for persona directories
                        for subdir_name in ["llm_personas", "personas"]:
                            sub_personas_dir = os.path.join(sub_dir, subdir_name)
                            if (
                                os.path.isdir(sub_personas_dir)
                                and sub_personas_dir not in persona_dirs
                            ):
                                persona_dirs.append(sub_personas_dir)

                        # Check for snippet directories
                        for subdir_name in ["llm_snippets", "snippets"]:
                            sub_snippets_dir = os.path.join(sub_dir, subdir_name)
                            if (
                                os.path.isdir(sub_snippets_dir)
                                and sub_snippets_dir not in snippet_dirs
                            ):
                                snippet_dirs.append(sub_snippets_dir)

            # Log discovered directories
            logger = logging.getLogger(__name__)
            logger.info(f"Using persona directories: {persona_dirs}")
            logger.info(f"Using snippet directories: {snippet_dirs}")

            # Create MultiFileLoader with all directories
            loader = MultiFileLoader(personas_dirs=persona_dirs, snippets_dirs=snippet_dirs)
            store = MarkdownStore(settings.conversations_dir)
            client = adapter_class()

            _default_manager_instance = ChatManager(
                settings=settings,
                llm_client=client,
                persona_loader=loader,
                snippet_provider=loader,
                history_store=store,
                context_provider=context_provider,
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
]

# Add IPython extension entry points to __all__ if available
if _IPYTHON_AVAILABLE:
    __all__ += ["load_ipython_extension", "unload_ipython_extension"]
