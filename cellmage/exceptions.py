class NotebookLLMError(Exception):
    """Base exception for all cellmage errors."""

    pass


class ConfigurationError(NotebookLLMError):
    """Raised when there's a configuration error."""

    pass


class ResourceNotFoundError(NotebookLLMError):
    """Raised when a resource (persona, snippet) is not found."""

    pass


class LLMInteractionError(NotebookLLMError):
    """Raised when there's an error interacting with the LLM service."""

    pass


class HistoryManagementError(NotebookLLMError):
    """Raised when there's an error managing conversation history."""

    pass


class PersistenceError(NotebookLLMError):
    """Raised when there's an error saving or loading data."""

    pass


class SnippetError(NotebookLLMError):
    """Raised when there's an error with snippet operations."""

    pass
