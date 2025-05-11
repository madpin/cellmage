import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from tokencostauto import calculate_completion_cost, calculate_prompt_cost

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
from .model_mapping import ModelMapper
from .models import Message, PersonaConfig


class ChatManager:
    """
    Main class for managing LLM interactions.

    Coordinates between:
    - LLM client for sending requests
    - Persona loader for personality configurations
    - Snippet provider for loading snippets
    - Conversation manager for tracking conversation
    - Context provider for environment context
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClientInterface] = None,
        persona_loader: Optional[PersonaLoader] = None,
        snippet_provider: Optional[SnippetProvider] = None,
        history_store: Optional[HistoryStore] = None,  # Kept for compatibility, not used
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
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing ChatManager")

        # Set up components
        self.settings = settings or Settings()
        self.llm_client = llm_client
        self.persona_loader = persona_loader
        self.snippet_provider = snippet_provider

        # Initialize model mapper
        self.model_mapper = ModelMapper(auto_load=True)

        # Load model mappings if configured
        if self.settings.model_mappings_file:
            self.model_mapper.load_mappings(self.settings.model_mappings_file)
        elif self.settings.auto_find_mappings and context_provider:
            # Try to get notebook directory from context provider
            exec_context = context_provider.get_execution_context()
            if exec_context and len(exec_context) > 1 and exec_context[1]:
                notebook_dir = os.path.dirname(exec_context[1])
                mapping_file = ModelMapper.find_mapping_file(notebook_dir)
                if mapping_file:
                    self.model_mapper.load_mappings(mapping_file)

        # Store creation timestamp for auto-save filename
        self.creation_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Set up conversation manager (replaces history manager)
        self.conversation_manager = ConversationManager(context_provider=context_provider)
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

        # Always add the persona's system message if it has one
        if persona.system_message:
            # Get current history
            current_history = self.conversation_manager.get_messages()

            # Extract system and non-system messages
            system_messages = [m for m in current_history if m.role == "system"]
            non_system_messages = [m for m in current_history if m.role != "system"]

            # If there are existing system messages, we'll need to reorder
            if system_messages:
                # Clear the history
                self.conversation_manager.clear_messages(keep_system=False)

                # Add persona system message first
                self.conversation_manager.add_message(
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
                    self.conversation_manager.add_message(msg)

                # Re-add all non-system messages
                for msg in non_system_messages:
                    self.conversation_manager.add_message(msg)
            else:
                # No existing system messages, just add the persona's system message
                self.conversation_manager.add_message(
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
                    self.llm_client.set_override(key, value)
                elif key != "system_message":  # Skip system_message as it's handled separately
                    self.logger.debug(f"Skipping non-API parameter from persona config: {key}")

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
        self.conversation_manager.add_message(
            Message(
                role=role,
                content=snippet_content,
                id=Message.generate_message_id(
                    role=role,
                    content=snippet_content,
                    cell_id=None,
                    execution_count=None,
                ),
                is_snippet=True,
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
            self.conversation_manager.perform_rollback(cell_id)

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
            history_messages = (
                self.conversation_manager.get_messages() if self.conversation_manager else []
            )

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

            # Calculate cost using tokencostauto (with model alias mapping)
            try:
                # Map alias to full model name for cost calculation
                mapped_model_name = self.model_mapper.get_full_name(model_name)

                prompt_for_cost = [{"role": m.role, "content": m.content} for m in messages]
                completion_for_cost = (
                    str(assistant_response_content)
                    if assistant_response_content is not None
                    else ""
                )
                prompt_cost = calculate_prompt_cost(prompt_for_cost, mapped_model_name)
                completion_cost = calculate_completion_cost(completion_for_cost, mapped_model_name)
                cost_dollars = prompt_cost + completion_cost
            except Exception as e:
                self.logger.warning(f"Failed to calculate cost with tokencostauto: {e}")
                cost_dollars = 0.0
                prompt_cost = 0.0
                completion_cost = 0.0

            # Format cost as a string for display
            cost_str = f"{cost_dollars:f}"

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

                if self.conversation_manager:
                    self.conversation_manager.add_message(user_message)

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
                        "model_used": actual_model_used or model_name,
                    },
                    execution_count=exec_count,
                    cell_id=cell_id,
                )

                if self.conversation_manager:
                    self.conversation_manager.add_message(assistant_message)

                # Auto-save the conversation if enabled in settings
                if self.settings.auto_save and self.conversation_manager:
                    try:
                        saved_path = self.conversation_manager._save_current_conversation()
                        if saved_path:
                            self.logger.info(f"Auto-saved conversation to {saved_path}")
                    except Exception as e:
                        self.logger.warning(f"Failed to auto-save conversation: {e}")

            # Update the call to display_status in the success case
            # Display status bar if context provider is available
            duration = time.time() - start_time
            if self.context_provider is not None and not stream:
                # Always provide model_used and duration for status bar
                status_model = actual_model_used or model_name
                status_info = {
                    "success": True,
                    "duration": duration,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "total_tokens": total_tokens,
                    "cost_str": cost_str,
                    "model_used": status_model,  # Always use model_used key
                    "response_content": assistant_response_content,
                }
                self.context_provider.display_status(status_info)

            return assistant_response_content

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Error during chat: {e}")

            # Show error in status bar
            if self.context_provider is not None:
                status_info = {
                    "success": False,
                    "duration": duration,
                    "tokens_in": None,
                    "tokens_out": None,
                    "total_tokens": None,
                    "cost_str": None,
                    "model_used": None,
                    "response_content": f"Error: {str(e)}",
                }
                self.context_provider.display_status(status_info)

            # Re-raise to let caller handle
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
        return self.conversation_manager._save_current_conversation()

    def load_conversation(self, conversation_id: str) -> bool:
        """
        Load a conversation from a file.

        Args:
            conversation_id: ID of the conversation to load

        Returns:
            True if successful, False otherwise
        """
        return self.conversation_manager.load_conversation(conversation_id)

    def get_history(self) -> List[Message]:
        """
        Get the current conversation history.

        Returns:
            List of messages in the conversation
        """
        if self.conversation_manager:
            messages = self.conversation_manager.get_messages()

            # Additional debug to help diagnose any issues
            if messages:
                self.logger.info(f"Retrieved {len(messages)} messages from conversation manager")

                # Count message types for debugging
                role_counts = {}
                integration_counts = {}

                for msg in messages:
                    # Count by role
                    role = msg.role
                    role_counts[role] = role_counts.get(role, 0) + 1

                    # Count integration sources
                    if msg.metadata and "source" in msg.metadata:
                        source = msg.metadata.get("source")
                        if source:
                            integration_counts[source] = integration_counts.get(source, 0) + 1

                if role_counts:
                    self.logger.debug(f"Message types in history: {role_counts}")
                if integration_counts:
                    self.logger.debug(f"Integration sources in history: {integration_counts}")
            else:
                self.logger.warning("Conversation manager returned empty history")

            return messages

        self.logger.warning("No conversation manager available when trying to get history")
        return []

    def clear_history(self, keep_system: bool = True) -> None:
        """
        Clear the conversation history.

        Args:
            keep_system: Whether to keep system messages
        """
        self.conversation_manager.clear_messages(keep_system=keep_system)

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

        if any(sensitive_part in key.lower() for sensitive_part in sensitive_keys) and isinstance(
            value, str
        ):
            if len(value) > 8:
                return value[:4] + "..." + value[-2:]
            else:
                return "***"  # For very short values
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

        # Access the internal _instance_overrides attribute of the LLM client if it exists
        if hasattr(self.llm_client, "_instance_overrides"):
            raw_overrides = self.llm_client._instance_overrides.copy()
            masked_overrides = {
                k: self._mask_sensitive_value(k, v) for k, v in raw_overrides.items()
            }
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
