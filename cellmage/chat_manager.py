import uuid
import time
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .config import Settings
from .models import Message, PersonaConfig
from .history_manager import HistoryManager
from .interfaces import (
    LLMClientInterface,
    PersonaLoader,
    SnippetProvider,
    HistoryStore,
    ContextProvider,
    StreamCallbackHandler
)
from .exceptions import (
    NotebookLLMError,
    ConfigurationError,
    ResourceNotFoundError,
    LLMInteractionError
)


class ChatManager:
    """
    Main class for managing LLM interactions.
    
    Coordinates between:
    - LLM client for sending requests
    - Persona loader for personality configurations
    - Snippet provider for loading snippets
    - History manager for tracking conversation
    - Context provider for environment context
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClientInterface] = None,
        persona_loader: Optional[PersonaLoader] = None,
        snippet_provider: Optional[SnippetProvider] = None,
        history_store: Optional[HistoryStore] = None,
        context_provider: Optional[ContextProvider] = None
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
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing ChatManager")
        
        # Set up components
        self.settings = settings or Settings()
        self.llm_client = llm_client
        self.persona_loader = persona_loader
        self.snippet_provider = snippet_provider
        
        # Set up history manager
        self.history_manager = HistoryManager(
            history_store=history_store,
            context_provider=context_provider
        )
        self.context_provider = context_provider
        
        # Set up session
        self._session_id = str(uuid.uuid4())
        self._active_persona: Optional[PersonaConfig] = None
        
        # Initialize with default persona if specified
        if self.settings.default_persona and self.persona_loader:
            try:
                self.set_default_persona(self.settings.default_persona)
            except Exception as e:
                self.logger.warning(f"Failed to set default persona: {e}")
        
        # Initialize with default model if specified
        if self.settings.default_model and self.llm_client:
            try:
                self.llm_client.set_override("model", self.settings.default_model)
            except Exception as e:
                self.logger.warning(f"Failed to set default model: {e}")
        
        self.logger.info("ChatManager initialized")
    
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update the settings.
        
        Args:
            settings: Dictionary of settings to update
        """
        if self.settings:
            self.settings.update(**settings)
            self.logger.info("Settings updated")
    
    def set_default_persona(self, name: str) -> None:
        """
        Set the default persona.
        
        Args:
            name: Name of the persona
            
        Raises:
            ResourceNotFoundError: If the persona doesn't exist
        """
        if not self.persona_loader:
            raise ConfigurationError("No persona loader configured")
        
        persona = self.persona_loader.get_persona(name)
        if not persona:
            raise ResourceNotFoundError(f"Persona '{name}' not found")
        
        self._active_persona = persona
        
        # Add system message if not already in history
        system_messages = [m for m in self.history_manager.get_history() if m.role == "system"]
        if not system_messages and persona.system_message:
            # Add system message to history
            self.history_manager.add_message(
                Message(
                    role="system",
                    content=persona.system_message,
                    id=str(uuid.uuid4())
                )
            )
        
        # Set client overrides if specified in persona config
        if self.llm_client and persona.config:
            for key, value in persona.config.items():
                if key != "system_message":  # Skip system message as it's handled separately
                    self.llm_client.set_override(key, value)
        
        self.logger.info(f"Default persona set to '{name}'")
    
    def add_snippet(self, name: str, role: str = "system") -> bool:
        """
        Add a snippet as a message to the conversation.
        
        Args:
            name: Name of the snippet
            role: Role for the snippet message ("system", "user", or "assistant")
            
        Returns:
            True if the snippet was added, False otherwise
        """
        if not self.snippet_provider:
            self.logger.warning("No snippet provider configured")
            return False
        
        # Validate role
        valid_roles = {"system", "user", "assistant"}
        if role not in valid_roles:
            self.logger.error(f"Invalid role '{role}' for snippet. Valid roles are: {valid_roles}")
            return False
        
        # Load snippet
        snippet_content = self.snippet_provider.get_snippet(name)
        if not snippet_content:
            self.logger.warning(f"Snippet '{name}' not found")
            return False
        
        # Add to history
        self.history_manager.add_message(
            Message(
                role=role,
                content=snippet_content,
                id=str(uuid.uuid4()),
                is_snippet=True
            )
        )
        
        self.logger.info(f"Added snippet '{name}' as {role} message")
        return True
    
    def chat(
        self, 
        prompt: str,
        persona_name: Optional[str] = None, 
        model: Optional[str] = None,
        stream: bool = True,
        add_to_history: bool = True,
        auto_rollback: bool = True,
        execution_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Send a message to the LLM and get a response.
        
        Args:
            prompt: The user's message
            persona_name: Override the persona to use
            model: Override the model to use
            stream: Whether to stream the response
            add_to_history: Whether to add the message to history
            auto_rollback: Whether to check for and perform history rollback
            execution_context: Execution context data if already determined
            **kwargs: Additional parameters to pass to the LLM
            
        Returns:
            The LLM's response or None if failed
        """
        if not self.llm_client:
            raise ConfigurationError("No LLM client configured")
        
        start_time = time.time()
        user_message_added = False
        model_name = model or self.settings.default_model
        
        try:
            # Create user message
            user_message = Message(role="user", content=prompt, id=str(uuid.uuid4()))
            
            # Add user message to history
            if add_to_history:
                self.history_manager.add_message(user_message)
                user_message_added = True
            
            # Prepare messages for LLM
            messages = self.history_manager.get_history()
            
            # Add system message if persona is active
            if self._active_persona and self._active_persona.system_message:
                messages.insert(0, Message(role="system", content=self._active_persona.system_message, id=str(uuid.uuid4())))
            
            # Prepare LLM parameters
            llm_params = {"model": model_name}
            llm_params.update(kwargs)
            
            # Setup stream handler if streaming is enabled
            stream_callback = None
            if stream and self.context_provider:
                # Create a simple stream handler that uses context_provider to display updates
                display_handle = self.context_provider.display_stream_start()
                
                def stream_handler(chunk: str) -> None:
                    """Handle streaming chunks by updating display"""
                    nonlocal display_handle
                    if display_handle and self.context_provider:
                        self.context_provider.update_stream(display_handle, chunk)
                
                stream_callback = stream_handler
            
            # Call LLM client
            assistant_response_content = self.llm_client.chat(
                messages=messages, 
                stream=stream, 
                stream_callback=stream_callback, 
                **llm_params
            )
            
            # Estimate token counts
            # This is a naive implementation - ideally the LLM adapter should return this information
            input_text = "\n".join([m.content for m in messages])
            # Rough estimate: 1 token ≈ 4 chars for English text
            tokens_in = max(1, len(input_text) // 4)
            tokens_out = max(1, len(assistant_response_content) // 4)
            
            # Calculate cost - simplified model for now
            # Based on rough OpenAI-style pricing (actual cost depends on model)
            cost_mili_cents = int((tokens_in * 0.005 + tokens_out * 0.015) * 1000)
            
            # Format cost string with appropriate unit
            if cost_mili_cents < 1000:  # Less than 1 cent
                cost_str = f"{cost_mili_cents/1000:.4f}¢"  # Show as fraction of cent
            elif cost_mili_cents < 100000:  # Less than $1
                cost_str = f"{cost_mili_cents/1000:.2f}¢"  # Show as cents with ¢ symbol
            else:  # $1 or more
                cost_str = f"${cost_mili_cents/100000:.2f}"  # Show as dollars with $ symbol
            
            # Update user message metadata with token counts
            if add_to_history and len(self.history_manager.get_history()) >= 1:
                # Find the user message and update its metadata
                user_messages = [m for m in self.history_manager.get_history() if m.role == "user"]
                if user_messages:
                    latest_user_msg = user_messages[-1]
                    latest_user_msg.metadata["tokens_in"] = tokens_in
            
            # Create assistant message with metadata
            assistant_message = Message(
                role="assistant", 
                content=assistant_response_content, 
                id=str(uuid.uuid4()),
                metadata={
                    "model_used": model_name,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_mili_cents": cost_mili_cents,
                    "cost_str": cost_str
                }
            )
            
            # Add assistant message to history
            if add_to_history:
                self.history_manager.add_message(assistant_message)
            
            # Display status via context provider
            if self.context_provider:
                self.context_provider.display_status(
                    success=True,
                    duration=time.time() - start_time,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_mili_cents=cost_mili_cents,
                    model=model_name
                )
            
            return assistant_response_content
        
        except Exception as e:
            self.logger.error(f"Error during chat: {e}")
            if add_to_history and user_message_added:
                try:
                    # Use the correct method name for history management
                    if hasattr(self.history_manager, "revert_last_turn"):
                        self.history_manager.revert_last_turn()
                    elif hasattr(self.history_manager, "revert_last_message"):
                        self.history_manager.revert_last_message()
                    else:
                        # Fallback - try to remove the last message manually
                        history = self.history_manager.get_history()
                        if history and len(history) > 0:
                            self.history_manager.clear_history(keep_system=True)
                            # Add back all messages except the last one
                            for msg in history[:-1]:
                                self.history_manager.add_message(msg)
                    self.logger.debug("Reverted user message after error")
                except Exception as revert_error:
                    self.logger.error(f"Failed to revert user message: {revert_error}")
            
            # Display error status
            if self.context_provider:
                self.context_provider.display_status(
                    success=False,
                    duration=time.time() - start_time,
                    tokens_in=0,
                    tokens_out=0,
                    cost_mili_cents=0,
                    model=model_name
                )
                
            raise
    
    def list_personas(self) -> List[str]:
        """
        List available personas.
        
        Returns:
            List of persona names
        """
        if not self.persona_loader:
            self.logger.warning("No persona loader configured")
            return []
        
        return self.persona_loader.list_personas()
    
    def list_snippets(self) -> List[str]:
        """
        List available snippets.
        
        Returns:
            List of snippet names
        """
        if not self.snippet_provider:
            self.logger.warning("No snippet provider configured")
            return []
        
        return self.snippet_provider.list_snippets()
    
    def save_conversation(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Save the current conversation to a file.
        
        Args:
            filename: Base filename to use for saving
            
        Returns:
            Path to the saved file or None if failed
        """
        return self.history_manager.save_conversation(filename)
    
    def load_conversation(self, filepath: str) -> bool:
        """
        Load a conversation from a file.
        
        Args:
            filepath: Path to the file to load
            
        Returns:
            True if successful, False otherwise
        """
        return self.history_manager.load_conversation(filepath)
    
    def get_history(self) -> List[Message]:
        """
        Get the current conversation history.
        
        Returns:
            List of messages in the conversation
        """
        return self.history_manager.get_history()
    
    def clear_history(self, keep_system: bool = True) -> None:
        """
        Clear the conversation history.
        
        Args:
            keep_system: Whether to keep system messages
        """
        self.history_manager.clear_history(keep_system=keep_system)
    
    def set_override(self, key: str, value: Any) -> None:
        """
        Set an override parameter for the LLM.
        
        Args:
            key: Parameter name
            value: Parameter value
        """
        if not self.llm_client:
            self.logger.warning("No LLM client configured")
            return
        
        self.llm_client.set_override(key, value)
    
    def remove_override(self, key: str) -> None:
        """
        Remove an override parameter.
        
        Args:
            key: Parameter name to remove
        """
        if not self.llm_client:
            self.logger.warning("No LLM client configured")
            return
        
        self.llm_client.remove_override(key)
    
    def clear_overrides(self) -> None:
        """Clear all override parameters."""
        if not self.llm_client:
            self.logger.warning("No LLM client configured")
            return
        
        self.llm_client.clear_overrides()
    
    def _mask_sensitive_value(self, key: str, value: Any) -> Any:
        """
        Mask sensitive values like API keys for display purposes.
        
        Args:
            key: The parameter name
            value: The parameter value
            
        Returns:
            Masked value if sensitive, original value otherwise
        """
        sensitive_keys = ["api_key", "secret", "password", "token"]
        
        if any(sensitive_part in key.lower() for sensitive_part in sensitive_keys) and isinstance(value, str):
            if len(value) > 8:
                return value[:4] + "..." + value[-2:]
            else:
                return "***" # For very short values
        return value
    
    def get_overrides(self) -> Dict[str, Any]:
        """
        Get the current LLM parameter overrides.
        
        Returns:
            A dictionary of current override parameters with sensitive values masked
        """
        if not self.llm_client:
            self.logger.warning("No LLM client configured")
            return {}
        
        # Access the internal _instance_overrides attribute of the LLM client
        if hasattr(self.llm_client, "_instance_overrides"):
            raw_overrides = self.llm_client._instance_overrides.copy()
            # Mask sensitive values
            masked_overrides = {k: self._mask_sensitive_value(k, v) for k, v in raw_overrides.items()}
            return masked_overrides
        else:
            self.logger.warning("LLM client does not have _instance_overrides attribute")
            return {}
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get a list of available models from the LLM service.
        
        Returns:
            List of model info dictionaries
        """
        if not self.llm_client:
            self.logger.warning("No LLM client configured")
            return []
        
        return self.llm_client.get_available_models()
    
    def get_active_persona(self) -> Optional[PersonaConfig]:
        """
        Get the currently active persona configuration.
        
        Returns:
            The active persona config or None if no persona is active
        """
        return self._active_persona
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model information dictionary or None if not found
        """
        if not self.llm_client:
            self.logger.warning("No LLM client configured")
            return None
        
        return self.llm_client.get_model_info(model_name)

