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
        model: Optional[str] = None,
        persona_name: Optional[str] = None,
        stream: bool = True,
        add_to_history: bool = True,
        auto_rollback: bool = True,
        **kwargs
    ) -> Optional[str]:
        """
        Send a message to the LLM and get a response.
        
        Args:
            prompt: The message to send
            model: Override model to use for this request
            persona_name: Override persona to use for this request
            stream: Whether to stream the response
            add_to_history: Whether to add this exchange to history
            auto_rollback: Whether to check for and perform history rollback
            **kwargs: Additional parameters for the LLM
            
        Returns:
            The model's response as a string
        """
        if not self.llm_client:
            raise ConfigurationError("No LLM client configured")
        
        # Start timer for timing the response
        start_time = time.time()
        
        # Check for and handle cell re-execution
        if auto_rollback:
            self.history_manager.check_and_rollback()
        
        # Handle persona override
        temp_persona = None
        if persona_name and self.persona_loader:
            temp_persona = self.persona_loader.get_persona(persona_name)
            if not temp_persona:
                self.logger.warning(f"Persona '{persona_name}' not found")
        
        # Use temp persona or active persona
        persona = temp_persona or self._active_persona
        
        # Create user message
        user_message = Message(
            role="user",
            content=prompt,
            id=str(uuid.uuid4())
        )
        
        # Add user message to history if requested
        if add_to_history:
            self.history_manager.add_message(user_message)
        
        # Prepare messages for the LLM client
        messages = self.history_manager.get_history() if add_to_history else []
        
        # If not using history or no messages yet, but we have a persona with system message,
        # add it as the first message
        if (not messages or all(m.role != "system" for m in messages)) and persona and persona.system_message:
            messages.insert(0, Message(
                role="system",
                content=persona.system_message,
                id=str(uuid.uuid4())
            ))
        
        # If not using history, add the user message
        if not add_to_history:
            messages.append(user_message)
        
        # Prepare LLM client parameters
        llm_params = {}
        
        # Add model override if specified
        if model:
            llm_params["model"] = model
        
        # Add persona config params if available
        if persona and persona.config:
            for key, value in persona.config.items():
                if key != "system_message":  # Skip system message as it's handled separately
                    llm_params[key] = value
        
        # Add any additional parameters
        llm_params.update(kwargs)
        
        # Create stream callback if streaming is enabled
        stream_callback = None
        display_object = None
        if stream and self.context_provider:
            # Set up streaming display
            display_object = self.context_provider.display_stream_start()
            
            # Create stream callback that updates the display
            def update_stream(content_chunk: str) -> None:
                nonlocal full_content
                full_content += content_chunk
                if display_object:
                    self.context_provider.update_stream(display_object, full_content)
            
            stream_callback = update_stream
        
        # Initialize full content for streaming
        full_content = ""
        
        try:
            # Call the LLM client
            self.logger.info(f"Sending message to LLM with {len(messages)} messages in context")
            response = self.llm_client.chat(
                messages=messages,
                stream=stream,
                stream_callback=stream_callback,
                **llm_params
            )
            
            # For streaming, full_content was built in the callback
            # For non-streaming, use the response directly
            content = full_content if stream else response
            
            # Create assistant message
            assistant_message = Message(
                role="assistant",
                content=content,
                id=str(uuid.uuid4())
            )
            
            # Add assistant message to history if requested
            if add_to_history:
                self.history_manager.add_message(assistant_message)
            
            # Display full response if not streaming and auto_display is enabled
            if not stream and self.settings.auto_display and self.context_provider:
                self.context_provider.display_response(content)
            
            # Save conversation if auto_save is enabled
            if add_to_history and self.settings.auto_save:
                self.save_conversation(self.settings.autosave_file)
            
            # Calculate timing and display status if context provider available
            end_time = time.time()
            duration = end_time - start_time
            
            if self.context_provider:
                # Estimate token counts (rough approximation)
                tokens_in = len(prompt.split())
                tokens_out = len(content.split())
                
                # Estimate cost in millicents (simple approximation)
                cost_mili_cents = tokens_in * 1 + tokens_out * 3  # Simple cost model
                
                # Display status
                self.context_provider.display_status(
                    success=True,
                    duration=duration,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_mili_cents=cost_mili_cents
                )
            
            return content
            
        except Exception as e:
            # Calculate timing for error status
            end_time = time.time()
            duration = end_time - start_time
            
            if isinstance(e, LLMInteractionError):
                self.logger.error(f"LLM interaction error: {e}")
            else:
                self.logger.exception(f"Error during chat: {e}")
            
            # Display error status
            if self.context_provider:
                self.context_provider.display_status(
                    success=False,
                    duration=duration,
                    tokens_in=len(prompt.split()),
                    tokens_out=0,
                    cost_mili_cents=0
                )
            
            raise NotebookLLMError(f"Chat failed: {e}") from e
    
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
    
    def get_overrides(self) -> Dict[str, Any]:
        """
        Get the current LLM parameter overrides.
        
        Returns:
            A dictionary of current override parameters
        """
        if not self.llm_client:
            self.logger.warning("No LLM client configured")
            return {}
        
        # Access the internal _instance_overrides attribute of the LLM client
        if hasattr(self.llm_client, "_instance_overrides"):
            return self.llm_client._instance_overrides.copy()
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

