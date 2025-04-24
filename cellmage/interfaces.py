from typing import Protocol, List, Dict, Any, Optional, Tuple, AsyncGenerator, runtime_checkable
from .models import Message, PersonaConfig, ConversationMetadata

# Use runtime_checkable for isinstance checks if needed, otherwise optional
# @runtime_checkable
class LLMClientInterface(Protocol):
    """Interface for interacting with an LLM backend."""
    async def chat_completion(
        self,
        messages: List[Dict[str, str]], # List of {'role': ..., 'content': ...}
        model: str,
        stream: bool = False,
        api_key: Optional[str] = None, # Allow overriding config
        api_base: Optional[str] = None, # Allow overriding config
        **kwargs: Any # Passthrough for temperature, max_tokens, etc.
    ) -> Any: # Returns response object or async generator for streaming
        """Sends messages to the LLM and returns the response."""
        ...

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """(Optional) Fetches available models from the endpoint."""
        ...

# @runtime_checkable
class PersonaLoader(Protocol):
    """Interface for loading personality configurations."""
    def load(self, name: str) -> PersonaConfig:
        """Loads the configuration for the specified persona name."""
        ...

    def list_available(self) -> List[str]:
        """Lists the names of available personas."""
        ...

# @runtime_checkable
class SnippetProvider(Protocol):
    """Interface for retrieving text snippets."""
    def get(self, name: str) -> str:
        """Gets the content of the specified snippet name."""
        ...

    def list_available(self) -> List[str]:
        """Lists the names of available snippets."""
        ...

# @runtime_checkable
class HistoryStore(Protocol):
    """Interface for saving and loading conversation histories."""
    def save(self, messages: List[Message], metadata: ConversationMetadata) -> str:
        """Saves the history and returns an identifier (e.g., file path)."""
        ...

    def load(self, identifier: str) -> Tuple[List[Message], ConversationMetadata]:
        """Loads history and metadata using the identifier."""
        ...

    def list_saved(self) -> List[str]:
        """Lists identifiers of available saved histories."""
        ...

# @runtime_checkable
class ContextProvider(Protocol):
    """Interface for getting environment-specific context (optional)."""
    def get_current_context(self) -> Tuple[Optional[int], Optional[str]]:
        """Returns (execution_count, cell_id) if available, else (None, None)."""
        ...

# @runtime_checkable
class StreamCallbackHandler(Protocol):
    """Interface for handling streaming LLM responses."""
    def on_stream_start(self) -> None:
        """Called when the stream begins."""
        ...

    def on_stream_chunk(self, chunk: str) -> None:
        """Called for each piece of content received."""
        ...

    def on_stream_end(self, full_response: str) -> None:
        """Called when the stream finishes, with the complete response."""
        ...

    def on_stream_error(self, error: Exception) -> None:
        """Called if an error occurs during streaming."""
        ...
