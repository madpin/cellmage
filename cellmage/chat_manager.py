"""
DEPRECATED: ChatManager compatibility wrapper.

This module is maintained only for backward compatibility and will be removed in a future version.
All new code should use ConversationManager directly.
"""

import logging
import os
import time
import uuid
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Import wrapped components
from .config import Settings
from .conversation_manager import ConversationManager
from .exceptions import ConfigurationError, ResourceNotFoundError
from .interfaces import (
    ContextProvider,
    HistoryStore,
    LLMClientInterface,
    PersonaLoader,
    SnippetProvider,
)
from .models import Message, PersonaConfig

# Set up deprecation warning for module import
warnings.warn(
    "The chat_manager module is deprecated and will be removed in a future version. "
    "Use conversation_manager instead.",
    DeprecationWarning,
    stacklevel=2
)


class ChatManager:
    """
    DEPRECATED: Legacy compatibility wrapper around ConversationManager.
    
    This class is provided for backward compatibility only.
    New code should use ConversationManager directly.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClientInterface] = None,
        persona_loader: Optional[PersonaLoader] = None,
        snippet_provider: Optional[SnippetProvider] = None,
        history_store: Optional[HistoryStore] = None,
        context_provider: Optional[ContextProvider] = None,
    ):
        """
        Initialize the chat manager.

        Args:
            settings: Application settings
            llm_client: Client for LLM interactions
            persona_loader: Loader for persona configurations
            snippet_provider: Provider for snippets
            history_store: Store for conversation history
            context_provider: Provider for execution context
        """
        # Output deprecation warning on initialization
        warnings.warn(
            "ChatManager is deprecated and will be removed in a future version. "
            "Use ConversationManager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.warning(
            "ChatManager is deprecated and will be removed in a future version. "
            "Use ConversationManager instead."
        )
        
        # Create the underlying ConversationManager that powers this compatibility layer
        self._conversation_manager = ConversationManager(
            settings=settings,
            llm_client=llm_client,
            persona_loader=persona_loader,
            snippet_provider=snippet_provider,
            context_provider=context_provider,
            history_store=history_store
        )
        
        # Store references to key components for backward compatibility
        self.settings = settings or Settings()
        self.llm_client = llm_client
        self.persona_loader = persona_loader
        self.snippet_provider = snippet_provider
        self.context_provider = context_provider
        
        # Legacy handler for history
        self.history_manager = LegacyHistoryManager(self._conversation_manager)
        
        # Store creation timestamp for auto-save filename (for backward compat)
        self.creation_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Session ID for backward compatibility
        self._session_id = str(uuid.uuid4())
        
        # Expose the active persona
        self._active_persona = self._conversation_manager._active_persona
        
        # Expose model mapper
        self.model_mapper = self._conversation_manager.model_mapper
        
        self.logger.info("ChatManager initialized (compatibility wrapper)")

    def update_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update the settings.

        Args:
            settings: Dictionary of settings to update
        """
        self._conversation_manager.update_settings(settings)

    def set_default_persona(self, name: str) -> None:
        """
        Set the default persona.

        Args:
            name: Name of the persona

        Raises:
            ResourceNotFoundError: If the persona doesn't exist
        """
        self._conversation_manager.set_default_persona(name)
        # Update the local reference
        self._active_persona = self._conversation_manager._active_persona

    def add_snippet(self, name: str, role: str = "system") -> bool:
        """
        Add a snippet as a message to the conversation.

        Args:
            name: Name of the snippet
            role: Role for the snippet message ("system", "user", or "assistant")

        Returns:
            True if the snippet was added, False otherwise
        """
        return self._conversation_manager.add_snippet(name, role)

    def chat(
        self,
        prompt: str,
        persona_name: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = True,
        add_to_history: bool = True,
        auto_rollback: bool = True,
        execution_context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[str]:
        """
        Send a message to the LLM and get a response.

        Args:
            prompt: The message to send
            persona_name: Optional persona to use for this message only
            model: Optional model to use for this message only
            stream: Whether to stream the response (default: True)
            add_to_history: Whether to add the message to conversation history
            auto_rollback: Whether to perform automatic rollback on cell re-execution
            execution_context: Optional explicit execution context (execution_count, cell_id)
            **kwargs: Additional parameters to pass to the LLM

        Returns:
            The LLM response text
        """
        return self._conversation_manager.chat(
            prompt=prompt,
            persona_name=persona_name,
            model=model,
            stream=stream,
            add_to_history=add_to_history,
            auto_rollback=auto_rollback,
            execution_context=execution_context,
            **kwargs
        )

    def list_personas(self) -> List[str]:
        """
        List available personas.

        Returns:
            List of persona names
        """
        return self._conversation_manager.list_personas()

    def list_snippets(self) -> List[str]:
        """
        List available snippets.

        Returns:
            List of snippet names
        """
        return self._conversation_manager.list_snippets()

    def save_conversation(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Save the current conversation to a file.

        Args:
            filename: Base filename to use for saving

        Returns:
            Path to the saved file or None if failed
        """
        # Use the original conversation manager's _save_current_conversation, but
        # allow setting a custom filename
        original_id = None
        if filename:
            original_id = self._conversation_manager.current_conversation_id
            self._conversation_manager.current_conversation_id = filename
        
        try:
            return self._conversation_manager._save_current_conversation()
        finally:
            # Restore the original conversation ID
            if original_id:
                self._conversation_manager.current_conversation_id = original_id

    def load_conversation(self, filepath: str) -> bool:
        """
        Load a conversation from a file.

        Args:
            filepath: Path to the file to load

        Returns:
            True if successful, False otherwise
        """
        return self._conversation_manager.load_conversation(filepath)

    def get_history(self) -> List[Message]:
        """
        Get the current conversation history.

        Returns:
            List of messages in the conversation
        """
        return self._conversation_manager.get_messages()

    def clear_history(self, keep_system: bool = True) -> None:
        """
        Clear the conversation history.

        Args:
            keep_system: Whether to keep system messages
        """
        self._conversation_manager.clear_messages(keep_system=keep_system)

    def set_override(self, key: str, value: Any) -> None:
        """
        Set an override parameter for the LLM.

        Args:
            key: Parameter name
            value: Parameter value
        """
        self._conversation_manager.set_override(key, value)

    def remove_override(self, key: str) -> None:
        """
        Remove an override parameter.

        Args:
            key: Parameter name to remove
        """
        self._conversation_manager.remove_override(key)

    def clear_overrides(self) -> None:
        """Clear all override parameters."""
        self._conversation_manager.clear_overrides()

    def _mask_sensitive_value(self, key: str, value: Any) -> Any:
        """
        Mask sensitive values like API keys for display purposes.

        Args:
            key: The parameter name
            value: The parameter value

        Returns:
            Masked value if sensitive, original value otherwise
        """
        return self._conversation_manager._mask_sensitive_value(key, value)

    def get_overrides(self) -> Dict[str, Any]:
        """
        Get the current LLM parameter overrides.

        Returns:
            A dictionary of current override parameters with sensitive values masked
        """
        return self._conversation_manager.get_overrides()

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get a list of available models from the LLM service.

        Returns:
            List of model info dictionaries
        """
        return self._conversation_manager.get_available_models()

    def get_active_persona(self) -> Optional[PersonaConfig]:
        """
        Get the currently active persona configuration.

        Returns:
            The active persona config or None if no persona is active
        """
        return self._conversation_manager.get_active_persona()

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Model information dictionary or None if not found
        """
        return self._conversation_manager.get_model_info(model_name)

    def _deduplicate_messages(self, messages: List[Message]) -> List[Message]:
        """
        Deduplicate messages to avoid sending duplicates to the LLM.

        Args:
            messages: List of messages to deduplicate

        Returns:
            Deduplicated list of messages
        """
        return self._conversation_manager._deduplicate_messages(messages)


class LegacyHistoryManager:
    """
    A compatibility wrapper around ConversationManager to provide HistoryManager interface.
    
    This class is used internally by the ChatManager compatibility layer.
    """
    
    def __init__(self, conversation_manager: ConversationManager):
        """
        Initialize a legacy history manager.
        
        Args:
            conversation_manager: The underlying ConversationManager
        """
        self.conversation_manager = conversation_manager
        self.logger = logging.getLogger(__name__)
        
    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation.
        
        Args:
            message: Message to add
        """
        self.conversation_manager.add_message(message)
        
    def get_history(self) -> List[Message]:
        """
        Get the conversation history.
        
        Returns:
            List of messages
        """
        return self.conversation_manager.get_messages()
        
    def clear_history(self, keep_system: bool = True) -> None:
        """
        Clear the conversation history.
        
        Args:
            keep_system: Whether to keep system messages
        """
        self.conversation_manager.clear_messages(keep_system=keep_system)
        
    def perform_rollback(self, cell_id: str) -> bool:
        """
        Perform rollback for cell rerun.
        
        Args:
            cell_id: Cell ID to rollback
            
        Returns:
            True if rollback was performed, False otherwise
        """
        return self.conversation_manager.perform_rollback(cell_id)
        
    def save_conversation(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Save conversation to a file.
        
        Args:
            filename: Base filename to use for saving
            
        Returns:
            Path to saved file or None on failure
        """
        original_id = None
        if filename:
            original_id = self.conversation_manager.current_conversation_id
            self.conversation_manager.current_conversation_id = filename
        
        try:
            return self.conversation_manager._save_current_conversation()
        finally:
            # Restore the original conversation ID
            if original_id:
                self.conversation_manager.current_conversation_id = original_id
                
    def load_conversation(self, filepath: str) -> bool:
        """
        Load conversation from a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            True if successful, False otherwise
        """
        return self.conversation_manager.load_conversation(filepath)
