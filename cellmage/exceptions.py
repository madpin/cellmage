class NotebookLLMError(Exception):
    """Base class for all package-specific errors."""
    pass

class ConfigurationError(NotebookLLMError):
    """Errors related to invalid or missing configuration."""
    pass

class ResourceNotFoundError(NotebookLLMError, FileNotFoundError):
    """Raised when a required resource (persona, snippet, history) cannot be found."""
    def __init__(self, resource_type: str, name_or_path: str):
        self.resource_type = resource_type
        self.name_or_path = name_or_path
        super().__init__(f"{resource_type.capitalize()} not found: '{name_or_path}'")

class LLMInteractionError(NotebookLLMError):
    """Errors occurring during interaction with the LLM API."""
    def __init__(self, message: str, original_exception: Exception | None = None):
        self.original_exception = original_exception
        super().__init__(message)

class HistoryManagementError(NotebookLLMError):
    """Errors related to managing the conversation history state."""
    pass

class PersistenceError(NotebookLLMError):
    """Errors related to saving or loading data."""
    pass

class SnippetError(NotebookLLMError):
    """Errors related to snippet processing."""
    pass
