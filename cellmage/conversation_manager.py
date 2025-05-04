"""
Conversation management module.

This module provides a ConversationManager class for managing conversations with different storage backends,
with SQLite as the default and recommended storage option.
"""

import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .config import Settings
from .exceptions import ConfigurationError, ResourceNotFoundError
from .interfaces import (
    ContextProvider,
    HistoryStore,
    LLMClientInterface,
    PersonaLoader,
    SnippetProvider,
    StreamCallbackHandler,
)
from .model_mapping import ModelMapper
from .models import ConversationMetadata, Message, PersonaConfig
from .storage.memory_store import MemoryStore
from .storage.sqlite_store import SQLiteStore
from .utils.token_utils import count_tokens


class ConversationManager:
    """
    Manages conversation data using configurable storage backends, with SQLite as default.

    This class provides methods for:
    - Creating, retrieving, updating, and deleting conversations
    - Managing messages within conversations
    - Interacting with LLM services
    - Managing personas and snippets
    - Searching and filtering conversations
    - Retrieving conversation statistics and debugging information
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        context_provider: Optional[ContextProvider] = None,
        storage_type: str = "sqlite",
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClientInterface] = None,
        persona_loader: Optional[PersonaLoader] = None,
        snippet_provider: Optional[SnippetProvider] = None,
        history_store: Optional[HistoryStore] = None,
    ):
        """
        Initialize the conversation manager.

        Args:
            db_path: Path to storage (e.g., SQLite database file). If None, uses default location.
            context_provider: Optional context provider for execution context
            storage_type: Storage type to use ('sqlite', 'memory'). Defaults to 'sqlite'.
            settings: Application settings
            llm_client: Client for LLM interactions
            persona_loader: Loader for persona configurations
            snippet_provider: Provider for snippets
            history_store: Legacy history store (for backward compatibility)
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing ConversationManager")
        
        # Set up components
        self.settings = settings or Settings()
        self.llm_client = llm_client
        self.persona_loader = persona_loader
        self.snippet_provider = snippet_provider
        self.context_provider = context_provider
        
        # Initialize the appropriate storage backend
        self.storage_type = storage_type.lower()
        self._init_storage(db_path)
        
        # If history_store is provided (for backward compatibility), use it
        if history_store:
            self.logger.info("Using provided history_store for backward compatibility")
            self.store = history_store
            
        # Set up manager state
        self.context_provider = context_provider
        self.current_conversation_id = str(uuid.uuid4())
        self.messages: List[Message] = []
        self.cell_last_message_index: Dict[str, int] = {}
        
        # Store creation timestamp for auto-save filename
        self.creation_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Set up persona tracking
        self._active_persona: Optional[PersonaConfig] = None
        
        # Initialize model mapper
        self.model_mapper = ModelMapper()
        self._initialize_model_mappings()
        
        # Initialize with default persona if specified
        self._initialize_default_persona()
        
        # Initialize with default model if specified
        self._initialize_default_model()

    def _init_storage(self, db_path: Optional[str] = None) -> None:
        """Initialize the storage backend based on storage_type."""
        if self.storage_type == "sqlite":
            self.store = SQLiteStore(db_path)
            self.logger.info(f"Using SQLite storage (default) at {db_path or 'default location'}")
        elif self.storage_type == "memory":
            self.store = MemoryStore()
            self.logger.info("Using in-memory storage (no persistence)")
        else:
            # Fallback to SQLite for unsupported storage types
            self.logger.warning(
                f"Storage type '{self.storage_type}' not supported. Using SQLite instead."
            )
            self.store = SQLiteStore(db_path)
            self.storage_type = "sqlite"

    def add_message(self, message: Message) -> str:
        """
        Add a message to the current conversation.

        Args:
            message: Message to add

        Returns:
            ID of the message
        """
        # If message doesn't have execution context, try to get it
        if (message.execution_count is None or message.cell_id is None) and self.context_provider:
            exec_count, cell_id = self.context_provider.get_execution_context()
            if message.execution_count is None:
                message.execution_count = exec_count
            if message.cell_id is None:
                message.cell_id = cell_id

        # Ensure message has an ID that's based on its content and context
        if not message.id:
            message.id = Message.generate_message_id(
                role=message.role,
                content=message.content,
                cell_id=message.cell_id,
                execution_count=message.execution_count,
            )

        # Add the message to our in-memory list
        self.messages.append(message)

        # Update cell tracking if we have a cell ID
        if message.cell_id:
            current_idx = len(self.messages) - 1
            self.cell_last_message_index[message.cell_id] = current_idx
            self.logger.debug(
                f"Updated tracking for cell ID {message.cell_id} to message index {current_idx}"
            )

        # Save to database
        self._save_current_conversation()

        # Log debug information
        if self.store:
            self.store.log_debug(
                self.current_conversation_id,
                "ConversationManager",
                "message_added",
                {
                    "message_id": message.id,
                    "role": message.role,
                    "content_length": len(message.content) if message.content else 0,
                    "has_cell_id": message.cell_id is not None,
                    "execution_count": message.execution_count,
                },
            )

        return message.id

    def get_messages(self) -> List[Message]:
        """
        Get a copy of the current messages.

        Returns:
            A copy of the messages list
        """
        return self.messages.copy()

    def perform_rollback(self, cell_id: Optional[str] = None) -> bool:
        """
        Perform a rollback for a particular cell ID if needed.

        Args:
            cell_id: Cell ID to rollback, or current cell if None

        Returns:
            True if rollback was performed, False otherwise
        """
        if not cell_id and self.context_provider:
            _, cell_id = self.context_provider.get_execution_context()

        if not cell_id:
            self.logger.debug("No cell ID available, skipping rollback check")
            return False

        # Check if this cell has been executed before
        if cell_id in self.cell_last_message_index:
            previous_end_index = self.cell_last_message_index[cell_id]

            # Only rollback if the previous message is still in history and was from the assistant
            if (
                0 <= previous_end_index < len(self.messages)
                and self.messages[previous_end_index].role == "assistant"
            ):
                # We need to remove the user message and assistant response for this cell
                start_index = previous_end_index - 1
                if start_index >= 0 and self.messages[start_index].role == "user":
                    self.logger.info(
                        f"Cell rerun detected (ID: {cell_id}). Rolling back history from {start_index}."
                    )

                    # Remove messages from this cell's previous execution
                    self.messages = self.messages[:start_index]

                    # Remove cell tracking
                    del self.cell_last_message_index[cell_id]

                    # Save changes to database
                    self._save_current_conversation()

                    # Log debug information
                    if self.store:
                        self.store.log_debug(
                            self.current_conversation_id,
                            "ConversationManager",
                            "rollback_performed",
                            {
                                "cell_id": cell_id,
                                "start_index": start_index,
                                "previous_end_index": previous_end_index,
                                "new_message_count": len(self.messages),
                            },
                        )

                    return True

        return False

    def clear_messages(self, keep_system: bool = True) -> None:
        """
        Clear the current conversation messages.

        Args:
            keep_system: Whether to keep system messages
        """
        if keep_system:
            # Keep system messages
            system_messages = [m for m in self.messages if m.role == "system"]
            self.messages = system_messages
        else:
            # Clear all messages
            self.messages = []

        # Clear cell tracking
        self.cell_last_message_index = {}

        # Save empty/system-only conversation
        self._save_current_conversation()

        self.logger.info(
            f"Messages cleared. Kept {len(self.messages)} system messages."
            if keep_system
            else "All messages cleared."
        )

    def create_new_conversation(self) -> str:
        """
        Create a new conversation and make it active.

        Returns:
            ID of the new conversation
        """
        # Save current conversation if it has messages
        if self.messages:
            self._save_current_conversation()

        # Create new conversation
        self.current_conversation_id = str(uuid.uuid4())
        self.messages = []
        self.cell_last_message_index = {}

        self.logger.info(f"Created new conversation with ID: {self.current_conversation_id}")
        return self.current_conversation_id

    def load_conversation(self, conversation_id: str) -> bool:
        """
        Load a conversation by ID and make it the active conversation.

        Args:
            conversation_id: ID of the conversation to load

        Returns:
            True if successful, False otherwise
        """
        try:
            # If the conversation_id doesn't start with sqlite://, add it
            if not conversation_id.startswith("sqlite://"):
                conversation_id = f"sqlite://{conversation_id}"

            # Load the conversation from SQLite
            messages, metadata = self.store.load_conversation(conversation_id)

            # Extract conversation ID from the URI
            if conversation_id.startswith("sqlite://"):
                self.current_conversation_id = conversation_id[len("sqlite://") :]
            else:
                self.current_conversation_id = conversation_id

            # Set as current conversation
            self.messages = messages

            # Clear cell tracking as the cell IDs from the loaded conversation
            # might not be relevant to the current session
            self.cell_last_message_index = {}

            self.logger.info(f"Loaded conversation {conversation_id} with {len(messages)} messages")
            return True

        except Exception as e:
            self.logger.error(f"Error loading conversation: {e}")
            return False

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation by ID.

        Args:
            conversation_id: ID of the conversation to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # If conversation is the current one, create a new conversation after deletion
            is_current = (
                self.current_conversation_id == conversation_id
                or f"sqlite://{self.current_conversation_id}" == conversation_id
            )

            # Delete from storage
            result = self.store.delete_conversation(conversation_id)

            # If this was the current conversation, create a new one
            if is_current and result:
                self.create_new_conversation()

            return result

        except Exception as e:
            self.logger.error(f"Error deleting conversation: {e}")
            return False

    def list_conversations(self) -> List[Dict[str, Any]]:
        """
        List all saved conversations.

        Returns:
            List of conversation metadata dictionaries
        """
        try:
            return self.store.list_saved_conversations()
        except Exception as e:
            self.logger.error(f"Error listing conversations: {e}")
            return []

    def search_conversations(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for conversations by content.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of matching conversation metadata
        """
        try:
            return self.store.search_conversations(query, limit)
        except Exception as e:
            self.logger.error(f"Error searching conversations: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored conversations.

        Returns:
            Dictionary with statistics
        """
        try:
            return self.store.get_statistics()
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}

    def add_tag(self, tag: str) -> bool:
        """
        Add a tag to the current conversation.

        Args:
            tag: Tag to add

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.store.add_tag(self.current_conversation_id, tag)
        except Exception as e:
            self.logger.error(f"Error adding tag: {e}")
            return False

    def remove_tag(self, tag: str) -> bool:
        """
        Remove a tag from the current conversation.

        Args:
            tag: Tag to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.store.remove_tag(self.current_conversation_id, tag)
        except Exception as e:
            self.logger.error(f"Error removing tag: {e}")
            return False

    def _calculate_token_usage(self) -> Dict[str, int]:
        """
        Calculate token usage for the current conversation.

        Returns:
            Dictionary with token counts
        """
        total_tokens = 0
        tokens_in = 0
        tokens_out = 0

        for message in self.messages:
            # If the message has token metadata, use it
            if message.metadata:
                message_tokens_in = message.metadata.get("tokens_in", 0)
                message_tokens_out = message.metadata.get("tokens_out", 0)
                tokens_in += message_tokens_in
                tokens_out += message_tokens_out
                total_tokens += message_tokens_in + message_tokens_out
            # Otherwise, estimate tokens for messages that don't have token counts
            elif message.content:
                # Use token_utils to count tokens in content
                message_tokens = count_tokens(message.content)
                # Add to total
                total_tokens += message_tokens
                # Store in metadata for future reference
                if not message.metadata:
                    message.metadata = {}
                if message.role == "user":
                    message.metadata["tokens_in"] = message_tokens
                    tokens_in += message_tokens
                elif message.role == "assistant":
                    message.metadata["tokens_out"] = message_tokens
                    tokens_out += message_tokens
                else:
                    # For system messages, count as input tokens
                    message.metadata["tokens_in"] = message_tokens
                    tokens_in += message_tokens

        return {"total_tokens": total_tokens, "tokens_in": tokens_in, "tokens_out": tokens_out}

    def _build_conversation_metadata(self) -> ConversationMetadata:
        """
        Build metadata for the current conversation.

        Returns:
            ConversationMetadata object
        """
        # Find current persona name and model if available
        persona_name = None
        model_name = None

        # Try to get model and persona from the most recent assistant message
        for message in reversed(self.messages):
            if message.role == "assistant" and message.metadata:
                if "model_used" in message.metadata:
                    model_name = message.metadata.get("model_used")

                # If we found a model, break
                if model_name:
                    break

        # Get token counts
        token_usage = self._calculate_token_usage()

        # Create metadata
        metadata = ConversationMetadata(
            session_id=self.current_conversation_id,
            saved_at=datetime.now(),
            persona_name=persona_name,
            model_name=model_name,
            total_tokens=token_usage["total_tokens"] if token_usage["total_tokens"] > 0 else None,
        )

        return metadata

    def _save_current_conversation(self) -> Optional[str]:
        """
        Save the current conversation to SQLite.

        Returns:
            URI of the saved conversation or None on failure
        """
        if not self.store:
            self.logger.error("Cannot save: No store configured")
            return None

        if not self.messages:
            self.logger.warning("Cannot save: No messages to save")
            return None

        try:
            # Build metadata
            metadata = self._build_conversation_metadata()

            # Save using the store
            self.logger.debug(f"Saving conversation with ID: {self.current_conversation_id}")
            save_path = self.store.save_conversation(
                messages=self.messages, metadata=metadata, filename=self.current_conversation_id
            )

            return save_path

        except Exception as e:
            self.logger.error(f"Error saving conversation: {e}")
            return None

    def _initialize_model_mappings(self) -> None:
        """Initialize model mappings from configuration."""
        # Load model mappings if configured
        if self.settings.model_mappings_file:
            self.model_mapper.load_mappings(self.settings.model_mappings_file)
        elif self.settings.auto_find_mappings and self.context_provider:
            # Try to get notebook directory from context provider
            exec_context = self.context_provider.get_execution_context()
            if exec_context and len(exec_context) > 1 and exec_context[1]:
                notebook_dir = os.path.dirname(exec_context[1])
                mapping_file = ModelMapper.find_mapping_file(notebook_dir)
                if mapping_file:
                    self.model_mapper.load_mappings(mapping_file)

    def _initialize_default_persona(self) -> None:
        """Initialize with default persona if specified."""
        if self.settings.default_persona and self.persona_loader:
            try:
                self.set_default_persona(self.settings.default_persona)
            except Exception as e:
                self.logger.warning(f"Failed to set default persona: {e}")

    def _initialize_default_model(self) -> None:
        """Initialize with default model if specified."""
        if self.settings.default_model and self.llm_client:
            try:
                self.set_override("model", self.settings.default_model)
            except Exception as e:
                self.logger.warning(f"Failed to set default model: {e}")

    def update_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update settings with new values.

        Args:
            settings: Dictionary with setting values to update
        """
        for key, value in settings.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
                self.logger.debug(f"Updated setting {key} = {value}")
            else:
                self.logger.warning(f"Unknown setting: {key}")

    def get_history(self) -> List[Message]:
        """
        Get the current conversation history.
        This method is provided for backward compatibility.

        Returns:
            List of messages in the conversation
        """
        return self.get_messages()

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

        # Always add the persona's system message if it has one
        if persona.system_message:
            # Get current messages
            current_messages = self.get_messages()

            # Extract system and non-system messages
            system_messages = [m for m in current_messages if m.role == "system"]
            non_system_messages = [m for m in current_messages if m.role != "system"]

            # If there are existing system messages, we'll need to reorder
            if system_messages:
                # Clear the messages
                self.clear_messages(keep_system=False)

                # Add persona system message first
                self.add_message(
                    Message(
                        role="system",
                        content=persona.system_message,
                        id=Message.generate_message_id(
                            role="system",
                            content=persona.system_message,
                            cell_id=None,
                            execution_count=None,
                        ),
                    )
                )

                # Re-add all existing system messages
                for msg in system_messages:
                    self.add_message(msg)

                # Re-add all non-system messages
                for msg in non_system_messages:
                    self.add_message(msg)
            else:
                # No existing system messages, just add the persona's system message
                self.add_message(
                    Message(
                        role="system",
                        content=persona.system_message,
                        id=Message.generate_message_id(
                            role="system",
                            content=persona.system_message,
                            cell_id=None,
                            execution_count=None,
                        ),
                    )
                )

        # Set client overrides if specified in persona config
        if self.llm_client and persona.config:
            # Define which fields are valid API parameters that should be passed to the LLM
            valid_llm_params = {
                "model",
                "temperature",
                "top_p",
                "n",
                "stream",
                "max_tokens",
                "presence_penalty",
                "frequency_penalty",
                "logit_bias",
                "stop",
            }

            for key, value in persona.config.items():
                # Only set override if it's a valid LLM API parameter
                if key in valid_llm_params:
                    self.set_override(key, value)
                elif key != "system_message":  # Skip system_message as it's handled separately
                    self.logger.debug(f"Skipping non-API parameter from persona config: {key}")

        self.logger.info(f"Default persona set to '{name}'")

    def add_snippet(self, name: str, role: str = "system") -> bool:
        """
        Add a snippet as a message.

        Args:
            name: Name of the snippet
            role: Message role for the snippet

        Returns:
            True if successful, False otherwise
        """
        if not self.snippet_provider:
            self.logger.warning("No snippet provider configured")
            return False

        snippet_content = self.snippet_provider.get_snippet(name)
        if not snippet_content:
            self.logger.warning(f"Snippet '{name}' not found")
            return False

        self.add_message(
            Message(
                role=role,
                content=snippet_content,
                id=Message.generate_message_id(
                    role=role,
                    content=snippet_content,
                    cell_id=None,
                    execution_count=None,
                ),
                metadata={"is_snippet": True}
            )
        )

        self.logger.info(f"Added snippet '{name}' as {role} message")
        return True

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

        if hasattr(self.llm_client, "clear_overrides"):
            self.llm_client.clear_overrides()
        else:
            self.logger.warning("LLM client does not support clearing overrides")

    def _deduplicate_messages(self, messages: List[Message]) -> List[Message]:
        """
        Deduplicate messages to avoid sending duplicates to the LLM.
        Preserves system messages from different sources (e.g., persona vs GitLab).
        Keeps the last occurrence of duplicate messages.

        Args:
            messages: List of messages to deduplicate

        Returns:
            Deduplicated list of messages
        """
        if not messages:
            return []

        # Special handling for system messages
        system_messages = [m for m in messages if m.role == "system"]
        non_system_messages = [m for m in messages if m.role != "system"]

        # Process non-system messages with standard deduplication
        # Iterate through messages in reverse order to keep the last occurrence
        seen_non_system = {}
        deduplicated_non_system = []

        for msg in reversed(non_system_messages):
            # Create a unique key based on role and content
            key = f"{msg.role}:{msg.content}"

            # If we haven't seen this message before, add it
            if key not in seen_non_system:
                seen_non_system[key] = True
                deduplicated_non_system.insert(
                    0, msg
                )  # Insert at beginning to preserve original order
            else:
                self.logger.debug(f"Skipping duplicate message with role '{msg.role}'")

        # For system messages, prioritize persona system messages but keep the last occurrence of duplicates
        persona_system = None
        content_system_messages = []

        # Simple heuristic: persona system messages are typically shorter than content messages
        # This keeps both persona messages and content (like GitLab data) as system messages
        if system_messages:
            # Sort by length, shortest first (likely the persona message)
            sorted_system = sorted(system_messages, key=lambda m: len(m.content))

            # The shortest is likely the persona system message
            persona_system = sorted_system[0] if sorted_system else None

            # Keep other system messages that aren't duplicates, preferring later occurrences
            seen_content = {persona_system.content} if persona_system else set()

            # Process content system messages in reverse order to keep the last occurrence
            for msg in reversed(sorted_system[1:] if persona_system else sorted_system):
                if msg.content not in seen_content:
                    content_system_messages.insert(0, msg)  # Insert at beginning to preserve order
                    seen_content.add(msg.content)
                else:
                    self.logger.debug("Skipping duplicate system message")

        # Combine messages in the correct order: system messages first, then non-system
        result = []
        if persona_system:
            result.append(persona_system)
        result.extend(content_system_messages)
        result.extend(deduplicated_non_system)

        if len(result) < len(messages):
            self.logger.info(f"Removed {len(messages) - len(result)} duplicate messages")

        return result

    def _mask_sensitive_value(self, key: str, value: Any) -> Any:
        """
        Mask sensitive values in settings or configurations.
        
        Args:
            key: Parameter name
            value: Parameter value
            
        Returns:
            Masked value if sensitive, original value otherwise
        """
        # List of keys that contain sensitive information
        sensitive_keys = {"api_key", "token", "password", "secret"}
        
        # Check if the key name might contain sensitive information
        for sensitive_key in sensitive_keys:
            if sensitive_key in key.lower():
                if isinstance(value, str):
                    # Show first 3 and last 3 characters only
                    if len(value) > 10:
                        return f"{value[:3]}...{value[-3:]}"
                    else:
                        # For shorter strings, just show that it's set
                        return "********"
                else:
                    return "<masked>"
                    
        # For non-sensitive keys, return the original value
        return value
        
    def get_active_persona(self) -> Optional[PersonaConfig]:
        """
        Get the current active persona.
        
        Returns:
            The active persona, or None if not set
        """
        return self._active_persona
        
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
        if self.llm_client is not None and hasattr(self.llm_client, "_instance_overrides"):
            raw_overrides = self.llm_client._instance_overrides.copy()
            # Mask sensitive values
            masked_overrides = {
                k: self._mask_sensitive_value(k, v) for k, v in raw_overrides.items()
            }
            return masked_overrides
        else:
            self.logger.warning("LLM client does not have _instance_overrides attribute")
            return {}
            
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get a list of available models from the LLM client.
        
        Returns:
            List of model information dictionaries
        """
        if not self.llm_client or not hasattr(self.llm_client, "get_available_models"):
            return []
        
        try:
            return self.llm_client.get_available_models()
        except Exception as e:
            self.logger.error(f"Failed to get available models: {e}")
            return []
            
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary with model information, or None if not found
        """
        if not self.model_mapper:
            return None
            
        return self.model_mapper.get_model_info(model_name)
        
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
        start_time = time.time()
        
        # Log persona usage for debugging
        self.logger.info(f"PERSONA DEBUG: Request made with persona_name='{persona_name}'")

        # Get execution context
        exec_count, cell_id = None, None
        if execution_context is not None:
            exec_count = execution_context.get("execution_count")
            cell_id = execution_context.get("cell_id")
        elif self.context_provider:
            exec_count, cell_id = self.context_provider.get_execution_context()

        # Log execution context
        if exec_count is not None:
            self.logger.debug(f"Execution count: {exec_count}")
        if cell_id is not None:
            self.logger.debug(f"Cell ID: {cell_id}")

        # Check for auto rollback
        if auto_rollback and cell_id is not None:
            self.perform_rollback(cell_id)

        try:
            # If persona_name is provided, try to load and set it temporarily
            temp_persona = None
            if persona_name:
                if self.persona_loader:
                    temp_persona = self.persona_loader.get_persona(persona_name)
                    if not temp_persona:
                        self.logger.warning(
                            f"Persona '{persona_name}' not found, using active persona instead."
                        )
                        # DEBUG: Log persona not found
                        self.logger.info(
                            f"PERSONA DEBUG: '{persona_name}' not found in available personas"
                        )
                        # List available personas for debugging
                        available_personas = self.persona_loader.list_personas()
                        self.logger.info(f"PERSONA DEBUG: Available personas: {available_personas}")
                    else:
                        self.logger.info(f"Using persona '{persona_name}' for this request")
                        # DEBUG: Log found persona and its system message
                        self.logger.info(
                            f"PERSONA DEBUG: Successfully loaded persona '{persona_name}'"
                        )
                        system_msg = (
                            temp_persona.system_message[:50] + "..."
                            if temp_persona.system_message and len(temp_persona.system_message) > 50
                            else temp_persona.system_message
                        )
                        self.logger.info(
                            f"PERSONA DEBUG: System message (truncated): '{system_msg}'"
                        )
                else:
                    self.logger.warning(
                        "No persona loader configured, ignoring persona_name parameter."
                    )

            # Get all message history
            history_messages = self.get_messages()

            # Extract non-system messages from history - we'll always keep these
            non_system_messages = [m for m in history_messages if m.role != "system"]

            # Prepare the messages list with system message(s) first, then other messages
            messages = []

            # FIXED: Handle system messages differently when using a temporary persona
            # Instead of keeping existing system messages from history when temp_persona is used,
            # use ONLY the temp_persona's system message for this request
            if temp_persona and temp_persona.system_message:
                # Use ONLY the temp persona's system message, replacing any existing ones just for this request
                system_message = Message(
                    role="system",
                    content=temp_persona.system_message,
                    id=Message.generate_message_id(
                        role="system",
                        content=temp_persona.system_message,
                        cell_id=cell_id,
                        execution_count=exec_count,
                    ),
                )
                messages.append(system_message)
                self.logger.debug(
                    f"Using system message from temporary persona '{persona_name}' for this request only"
                )
                # DEBUG: Record system message being used for this request
                self.logger.info(
                    f"PERSONA DEBUG: Using '{persona_name}' system message for this request"
                )
            else:
                # If no temp_persona, use system messages from history or active persona
                system_messages = [m for m in history_messages if m.role == "system"]
                if system_messages:
                    messages.extend(system_messages)
                    # DEBUG: Log which system messages are being used
                    for i, msg in enumerate(system_messages):
                        content_sample = (
                            msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                        )
                        self.logger.info(
                            f"PERSONA DEBUG: Using system message {i + 1} from history: '{content_sample}'"
                        )
                elif self._active_persona and self._active_persona.system_message:
                    system_message = Message(
                        role="system",
                        content=self._active_persona.system_message,
                        id=Message.generate_message_id(
                            role="system",
                            content=self._active_persona.system_message,
                            cell_id=cell_id,
                            execution_count=exec_count,
                        ),
                    )
                    messages.append(system_message)
                    self.logger.debug("Added system message from active persona")
                    # DEBUG: Log active persona being used
                    self.logger.info(
                        f"PERSONA DEBUG: Using system message from active persona '{self._active_persona.name}'"
                    )

            # Now add all non-system messages
            messages.extend(non_system_messages)

            # Setup stream handler if streaming is enabled
            stream_callback = None
            if stream and self.context_provider:
                # Create a simple stream handler that uses context_provider to display updates
                display_handle = self.context_provider.display_stream_start()

                def stream_handler(chunk: str) -> None:
                    """Handle streaming chunks by updating display"""
                    if display_handle is not None and self.context_provider is not None:
                        self.context_provider.update_stream(display_handle, chunk)
                    else:
                        # Fallback to print if display handle isn't available
                        print(chunk, end="", flush=True)

                stream_callback = stream_handler

            # Add the new user message
            user_message = Message(
                role="user",
                content=prompt,
                id=Message.generate_message_id(
                    role="user", content=prompt, cell_id=cell_id, execution_count=exec_count
                ),
                execution_count=exec_count,
                cell_id=cell_id,
            )

            # Add to messages we'll send to the LLM
            messages.append(user_message)

            # Deduplicate messages before sending to the LLM
            messages = self._deduplicate_messages(messages)

            # Figure out model to use with more robust fallbacks
            model_name = model

            # If model not specified directly, try to get it from the temp persona if available
            if (
                model_name is None
                and temp_persona
                and temp_persona.config
                and "model" in temp_persona.config
            ):
                model_name = temp_persona.config.get("model")
                self.logger.debug(f"Using model from temporary persona: {model_name}")

            # If still no model, try to get it from the active persona if available
            if (
                model_name is None
                and self._active_persona
                and self._active_persona.config
                and "model" in self._active_persona.config
            ):
                model_name = self._active_persona.config.get("model")
                self.logger.debug(f"Using model from active persona: {model_name}")

            # If still no model, check if LLM client has a model override set
            if (
                model_name is None
                and self.llm_client is not None
                and hasattr(self.llm_client, "_instance_overrides")
                and "model" in self.llm_client._instance_overrides
            ):
                model_name = self.llm_client._instance_overrides.get("model")
                self.logger.debug(f"Using model from LLM client override: {model_name}")

            # Final fallback to the default model from settings
            if model_name is None:
                model_name = self.settings.default_model
                self.logger.debug(f"Using default model from settings: {model_name}")

            # Ensure we have a model specified at this point
            if model_name is None:
                raise ConfigurationError(
                    "No model specified and no default model available in settings."
                )

            # Prepare LLM parameters
            llm_params = {}

            # Always set the model explicitly
            llm_params["model"] = model_name

            # Apply parameter overrides from temp persona if available
            if temp_persona and temp_persona.config:
                valid_llm_params = {
                    "temperature",
                    "top_p",
                    "n",
                    "stream",
                    "max_tokens",
                    "presence_penalty",
                    "frequency_penalty",
                    "logit_bias",
                    "stop",
                }
                for key, value in temp_persona.config.items():
                    if key in valid_llm_params:
                        llm_params[key] = value

            # FIX: Handle the 'overrides' parameter correctly
            # If there's an 'overrides' dictionary in kwargs, unpack its contents into llm_params
            if "overrides" in kwargs:
                if isinstance(kwargs["overrides"], dict):
                    self.logger.debug(f"Applying parameter overrides: {kwargs['overrides']}")
                    llm_params.update(kwargs["overrides"])
                else:
                    self.logger.warning(
                        f"Ignoring non-dictionary 'overrides': {kwargs['overrides']}"
                    )
                # Remove 'overrides' from kwargs to prevent it from being sent as a parameter
                del kwargs["overrides"]

            # Add any remaining kwargs to llm_params
            llm_params.update(kwargs)

            # Call LLM client
            self.logger.info(
                f"Sending message to LLM with {len(messages)} messages in context using model: {model_name}"
            )
            if self.llm_client is None:
                raise ConfigurationError("LLM client is not configured")

            assistant_response_content = self.llm_client.chat(
                messages=messages, stream=stream, stream_callback=stream_callback, **llm_params
            )

            # Get token usage data from the LLM client
            token_usage = {}
            if hasattr(self.llm_client, "get_last_token_usage"):
                token_usage = self.llm_client.get_last_token_usage()
                tokens_in = token_usage.get("prompt_tokens", 0)
                tokens_out = token_usage.get("completion_tokens", 0)
                total_tokens = token_usage.get("total_tokens", 0)
                self.logger.debug(
                    f"Token usage from API: {tokens_in} (prompt) + "
                    f"{tokens_out} (completion) = {total_tokens} (total)"
                )
            else:
                # Fallback to estimation if token usage isn't available from the client
                from .utils.token_utils import count_tokens

                # Get text content from messages
                input_text = "\n".join([m.content for m in messages])
                # Use proper token counting function
                tokens_in = count_tokens(input_text)

                # Ensure assistant_response_content is treated as a string for length calculation
                response_content_str = (
                    str(assistant_response_content)
                    if assistant_response_content is not None
                    else ""
                )
                tokens_out = count_tokens(response_content_str)
                
                total_tokens = tokens_in + tokens_out
                self.logger.debug(
                    f"Estimated token usage: {tokens_in} (prompt) + "
                    f"{tokens_out} (completion) = {total_tokens} (total)"
                )

            # Calculate cost - simplified model for now
            if model_name and "gpt-4" in model_name.lower():
                # Approximate GPT-4 rates
                cost_input = tokens_in * 0.03 / 1000  # $0.03 per 1K tokens
                cost_output = tokens_out * 0.06 / 1000  # $0.06 per 1K tokens
            else:
                # Generic/default rates
                cost_input = tokens_in * 0.01 / 1000  # $0.01 per 1K tokens
                cost_output = tokens_out * 0.02 / 1000  # $0.02 per 1K tokens

            cost_dollars = cost_input + cost_output

            # Convert to millicents (1/100,000 of a dollar) for consistent display
            cost_mili_cents = int(cost_dollars * 100000)

            # Format cost as a string for display
            cost_str = f"${cost_dollars:.6f}"

            # Get the actual model used from the LLM client
            actual_model_used = None
            if hasattr(self.llm_client, "get_last_model_used"):
                actual_model_used = self.llm_client.get_last_model_used()
            elif (
                hasattr(self.llm_client, "_instance_overrides")
                and "model" in self.llm_client._instance_overrides
            ):
                actual_model_used = self.llm_client._instance_overrides.get("model")

            # If we're adding to history, add both user and assistant messages
            if add_to_history and assistant_response_content:
                # Add user message to history WITH token count information
                user_message.metadata = {
                    "tokens_in": tokens_in,
                    "model_used": actual_model_used or model_name,
                }

                self.add_message(user_message)

                # Create and add assistant message
                assistant_message = Message(
                    role="assistant",
                    content=assistant_response_content,
                    id=Message.generate_message_id(
                        role="assistant",
                        content=assistant_response_content,
                        cell_id=cell_id,
                        execution_count=exec_count,
                    ),
                    metadata={
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "total_tokens": total_tokens,
                        "cost_str": cost_str,
                        "cost_mili_cents": cost_mili_cents,
                        "model_used": actual_model_used or model_name,
                    },
                    execution_count=exec_count,
                    cell_id=cell_id,
                )

                self.add_message(assistant_message)

                # Auto-save the conversation if enabled in settings
                if self.settings.auto_save:
                    try:
                        # Use the autosave_file setting with the fixed creation timestamp
                        autosave_filename = (
                            f"{self.settings.autosave_file}_{self.creation_datetime}"
                        )
                        saved_path = self._save_current_conversation()
                        if saved_path:
                            self.logger.info(f"Auto-saved conversation to {saved_path}")
                    except Exception as e:
                        self.logger.warning(f"Failed to auto-save conversation: {e}")

            # Update the call to display_status in the success case
            # Display status bar if context provider is available
            duration = time.time() - start_time
            if self.context_provider is not None and not stream:
                self.context_provider.display_status(
                    {
                        "success": True,
                        "duration": duration,
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "total_tokens": total_tokens,
                        "cost_str": cost_str,
                        "cost_mili_cents": cost_mili_cents,
                        "model": actual_model_used or model_name,
                        "response_content": assistant_response_content,
                    }
                )

            return assistant_response_content

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Error during chat: {e}")

            # Show error in status bar
            if self.context_provider is not None:
                self.context_provider.display_status(
                    {
                        "success": False,
                        "duration": duration,
                        "tokens_in": None,
                        "tokens_out": None,
                        "total_tokens": None,
                        "cost_str": None,
                        "cost_mili_cents": None,
                        "model": None,
                        "response_content": f"Error: {str(e)}",
                    }
                )

            # Re-raise to let caller handle
            raise
