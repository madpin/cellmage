from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .models import ConversationMetadata, Message, PersonaConfig

# Type definition for a stream callback function
StreamCallbackHandler = Callable[[str], None]


class LLMClientInterface(ABC):
    """Interface for LLM client adapters that handle communication with language models."""

    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        stream: bool = False,
        stream_callback: Optional[StreamCallbackHandler] = None,
        **kwargs,
    ) -> Union[str, None]:
        """
        Send messages to the LLM and get a response.

        Args:
            messages: List of Message objects to send
            model: Override model to use for this request
            stream: Whether to stream the response
            stream_callback: Callback to handle streaming responses
            **kwargs: Additional parameters for the LLM

        Returns:
            The model's response as a string
        """
        pass

    @abstractmethod
    def set_override(self, key: str, value: Any) -> None:
        """
        Set an instance-level override for LLM parameters.

        Args:
            key: The parameter name
            value: The parameter value
        """
        pass

    @abstractmethod
    def remove_override(self, key: str) -> None:
        """
        Remove an instance-level override.

        Args:
            key: The parameter name to remove
        """
        pass

    @abstractmethod
    def clear_overrides(self) -> None:
        """
        Remove all instance-level overrides.
        """
        pass

    @abstractmethod
    def get_overrides(self) -> Dict[str, Any]:
        """
        Get the current LLM parameter overrides.

        Returns:
            A dictionary of current override parameters
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Fetch available models from the configured endpoint.

        Returns:
            List of model dictionaries or empty list if failed
        """
        pass

    @abstractmethod
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific model.

        Args:
            model_name: The name of the model to query

        Returns:
            Dictionary with model information or None on error
        """
        pass


class PersonaLoader(ABC):
    """Interface for loading persona configurations from storage."""

    @abstractmethod
    def list_personas(self) -> List[str]:
        """
        List available personas.

        Returns:
            List of persona names
        """
        pass

    @abstractmethod
    def get_persona(self, name: str) -> Optional[PersonaConfig]:
        """
        Get a persona by name.

        Args:
            name: Name of the persona to retrieve

        Returns:
            Persona configuration or None if not found
        """
        pass


class SnippetProvider(ABC):
    """Interface for loading code or content snippets."""

    @abstractmethod
    def list_snippets(self) -> List[str]:
        """
        List available snippets.

        Returns:
            List of snippet names
        """
        pass

    @abstractmethod
    def get_snippet(self, name: str) -> Optional[str]:
        """
        Load a snippet by name.

        Args:
            name: Name of the snippet to load

        Returns:
            Snippet content or None if not found
        """
        pass


class HistoryStore(ABC):
    """Interface for storing and retrieving conversation history."""

    @abstractmethod
    def save_conversation(
        self,
        messages: List[Message],
        metadata: ConversationMetadata,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """
        Save a conversation to storage.

        Args:
            messages: List of messages in the conversation
            metadata: Metadata about the conversation
            filename: Optional filename (without extension) to use

        Returns:
            Path to the saved file or None on failure
        """
        pass

    @abstractmethod
    def load_conversation(self, filepath: str) -> Tuple[List[Message], ConversationMetadata]:
        """
        Load a conversation from storage.

        Args:
            filepath: Path to the conversation file

        Returns:
            Tuple of (messages, metadata)
        """
        pass

    @abstractmethod
    def list_saved_conversations(self) -> List[Dict[str, Any]]:
        """
        List available saved conversations.

        Returns:
            List of conversation metadata dicts with paths
        """
        pass


class ContextProvider(ABC):
    """Interface for providing execution context (cell IDs, etc.)."""

    @abstractmethod
    def get_execution_context(self) -> Tuple[Optional[int], Optional[str]]:
        """
        Get the current execution context.

        Returns:
            Tuple of (execution_count, cell_id)
        """
        pass

    @abstractmethod
    def display_markdown(self, content: str) -> None:
        """
        Display markdown content in the user interface.

        Args:
            content: Markdown content to display
        """
        pass

    @abstractmethod
    def display_response(self, content: str) -> None:
        """
        Display an assistant response in the user interface.

        Args:
            content: Response content to display
        """
        pass

    @abstractmethod
    def display_stream_start(self) -> Any:
        """
        Set up display for a streaming response.

        Returns:
            An object that can be used to update the display
        """
        pass

    @abstractmethod
    def update_stream(self, display_object: Any, content: str) -> None:
        """
        Update a streaming display with new content.

        Args:
            display_object: The display object from display_stream_start
            content: The content to display
        """
        pass

    @abstractmethod
    def display_status(self, status_info: Dict[str, Any]) -> None:
        """
        Display status information in the user interface.

        Args:
            status_info: Dictionary containing status information to display
        """
        pass
