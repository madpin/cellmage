import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import Settings
from .exceptions import ConfigurationError, ResourceNotFoundError
from .history_manager import HistoryManager
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
        self.model_mapper = ModelMapper()

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

        # Set up history manager
        self.history_manager = HistoryManager(
            history_store=history_store, context_provider=context_provider
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

        # Always add the persona's system message if it has one
        if persona.system_message:
            # Get current history
            current_history = self.history_manager.get_history()

            # Extract system and non-system messages
            system_messages = [m for m in current_history if m.role == "system"]
            non_system_messages = [m for m in current_history if m.role != "system"]

            # If there are existing system messages, we'll need to reorder
            if system_messages:
                # Clear the history
                self.history_manager.clear_history(keep_system=False)

                # Add persona system message first
                self.history_manager.add_message(
                    Message(role="system", content=persona.system_message, id=str(uuid.uuid4()))
                )

                # Re-add all existing system messages
                for msg in system_messages:
                    self.history_manager.add_message(msg)

                # Re-add all non-system messages
                for msg in non_system_messages:
                    self.history_manager.add_message(msg)
            else:
                # No existing system messages, just add the persona's system message
                self.history_manager.add_message(
                    Message(role="system", content=persona.system_message, id=str(uuid.uuid4()))
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
        self.history_manager.add_message(
            Message(role=role, content=snippet_content, id=str(uuid.uuid4()), is_snippet=True)
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
        Send a message to the LLM.

        Args:
            prompt: The user's message
            persona_name: Optional persona name to use for this call
            model: Optional model name to use for this call
            stream: Whether to stream the response
            add_to_history: Whether to add the messages to history
            auto_rollback: Whether to automatically rollback on cell re-execution
            execution_context: Optional execution context information
            **kwargs: Additional parameters to pass to the LLM client

        Returns:
            Assistant's response or None on error
        """
        # Start timing the call for performance tracking
        start_time = time.time()

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
            self.history_manager.perform_rollback(cell_id)

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
                    else:
                        self.logger.info(f"Using persona '{persona_name}' for this request")
                else:
                    self.logger.warning(
                        "No persona loader configured, ignoring persona_name parameter."
                    )

            # Get all message history
            history_messages = self.history_manager.get_history() if self.history_manager else []

            # Extract any system messages from history
            system_messages = [m for m in history_messages if m.role == "system"]
            non_system_messages = [m for m in history_messages if m.role != "system"]

            # Prepare the messages list with system message(s) first, then other messages
            messages = []

            # If we have system messages in history, add them first
            if system_messages:
                messages.extend(system_messages)
            # If no system messages in history but we have an active persona, add its system message
            elif temp_persona and temp_persona.system_message:
                # Use the temp persona's system message if provided
                system_message = Message(
                    role="system", content=temp_persona.system_message, id=str(uuid.uuid4())
                )
                messages.append(system_message)
                self.logger.debug("Added system message from temporary persona")
            elif self._active_persona and self._active_persona.system_message:
                system_message = Message(
                    role="system", content=self._active_persona.system_message, id=str(uuid.uuid4())
                )
                messages.append(system_message)
                self.logger.debug("Added system message from active persona")

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
                id=str(uuid.uuid4()),
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
                input_text = "\n".join([m.content for m in messages])
                # Rough estimate: 1 token ≈ 4 chars for English text
                tokens_in = max(1, len(input_text) // 4)

                # Ensure assistant_response_content is treated as a string for length calculation
                response_content_str = (
                    str(assistant_response_content)
                    if assistant_response_content is not None
                    else ""
                )
                tokens_out = max(1, len(response_content_str) // 4)
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

                if self.history_manager:
                    self.history_manager.add_message(user_message)

                # Create and add assistant message
                assistant_message = Message(
                    role="assistant",
                    content=assistant_response_content,
                    id=str(uuid.uuid4()),
                    metadata={
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "total_tokens": total_tokens,
                        "cost_str": cost_str,
                        "cost_mili_cents": cost_mili_cents,
                        "model_used": actual_model_used or model_name,
                    },
                )

                if self.history_manager:
                    self.history_manager.add_message(assistant_message)

                # Auto-save the conversation if enabled in settings
                if self.settings.auto_save and self.history_manager:
                    try:
                        # Use the autosave_file setting with the fixed creation timestamp
                        autosave_filename = (
                            f"{self.settings.autosave_file}_{self.creation_datetime}"
                        )
                        saved_path = self.history_manager.save_conversation(autosave_filename)
                        if saved_path:
                            self.logger.info(f"Auto-saved conversation to {saved_path}")
                    except Exception as e:
                        self.logger.warning(f"Failed to auto-save conversation: {e}")

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
                    }
                )

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
        if filename:
            # Add the creation timestamp to the filename to ensure consistency
            filename_with_date = f"{filename}_{self.creation_datetime}"
            return self.history_manager.save_conversation(filename_with_date)
        else:
            # If no filename provided, let the history manager handle it
            return self.history_manager.save_conversation(None)

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

        Args:
            messages: List of messages to deduplicate

        Returns:
            Deduplicated list of messages
        """
        if not messages:
            return []

        # Track seen message contents by role to prevent duplicates
        seen = {}
        deduplicated = []

        for msg in messages:
            # Create a unique key based on role and content
            key = f"{msg.role}:{msg.content}"

            # If we haven't seen this message before, add it
            if key not in seen:
                seen[key] = True
                deduplicated.append(msg)
            else:
                self.logger.debug(f"Skipping duplicate message with role '{msg.role}'")

        if len(deduplicated) < len(messages):
            self.logger.info(f"Removed {len(messages) - len(deduplicated)} duplicate messages")

        return deduplicated
