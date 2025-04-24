import logging
from typing import List, Optional, Dict, Any, Callable, Tuple, AsyncGenerator
from datetime import datetime
import uuid

from .config import Settings
from .models import Message, PersonaConfig, ConversationMetadata
from .exceptions import (
    ResourceNotFoundError, ConfigurationError, LLMInteractionError,
    HistoryManagementError, PersistenceError, SnippetError
)
from .interfaces import (
    LLMClientInterface, PersonaLoader, SnippetProvider, HistoryStore,
    ContextProvider, StreamCallbackHandler
)
from .history_manager import HistoryManager
from .utils.logging import get_logger # Assuming a get_logger function exists

class ChatManager:
    """Orchestrates LLM chat sessions, managing state, configuration, and interactions."""

    def __init__(
        self,
        settings: Settings,
        llm_client: LLMClientInterface,
        persona_loader: PersonaLoader,
        snippet_provider: SnippetProvider,
        history_store: HistoryStore,
        context_provider: Optional[ContextProvider] = None,
        initial_persona_name: Optional[str] = None,
        session_id: Optional[str] = None, # For loading existing sessions
    ):
        """
        Initializes the ChatManager.

        Args:
            settings: Application settings object.
            llm_client: Client for interacting with the LLM API.
            persona_loader: Loader for personality configurations.
            snippet_provider: Provider for text snippets.
            history_store: Storage handler for saving/loading history.
            context_provider: (Optional) Provider for environment context (e.g., cell ID).
            initial_persona_name: (Optional) Name of the persona to load initially.
            session_id: (Optional) ID of an existing session to load or use for saving.
        """
        self.settings = settings
        self._llm_client = llm_client
        self._persona_loader = persona_loader
        self._snippet_provider = snippet_provider
        self._history_store = history_store
        self._context_provider = context_provider
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        self._history_manager = HistoryManager()
        self._active_persona: Optional[PersonaConfig] = None
        self._instance_overrides: Dict[str, Any] = {} # For model, temp etc.
        self._session_id = session_id or self._generate_session_id() # Unique ID for this session

        self.logger.info(f"ChatManager initialized. Session ID: {self._session_id}")

        if session_id:
            try:
                self.load_session(session_id) # Attempt to load history if ID provided
            except ResourceNotFoundError:
                 self.logger.warning(f"Session ID '{session_id}' provided, but no existing history found. Starting new session.")
            except PersistenceError as e:
                 self.logger.error(f"Failed to load session '{session_id}': {e}. Starting new session.")

        if initial_persona_name:
            try:
                self.select_persona(initial_persona_name)
            except ResourceNotFoundError:
                 self.logger.error(f"Initial persona '{initial_persona_name}' not found.")
                 # Continue without a persona, or raise? For now, continue.
        elif not self._active_persona and not self._history_manager.get_history(): # Ensure persona if history empty
             self.logger.info("No initial persona selected for new session.")

    # --- Persona Management ---
    def select_persona(self, name: str) -> None:
        """Loads and activates a persona by name."""
        self.logger.debug(f"Attempting to select persona: {name}")
        try:
            new_persona = self._persona_loader.load(name)
            self._active_persona = new_persona
            self.logger.info(f"Activated persona: {name}")
            self._apply_persona_to_history()
        except ResourceNotFoundError as e:
            self.logger.error(f"Failed to select persona: {e}")
            raise # Re-raise for caller to handle
        except Exception as e:
             self.logger.exception(f"An unexpected error occurred while selecting persona '{name}'.")
             raise ConfigurationError(f"Failed to load persona '{name}': {e}") from e

    def get_active_persona(self) -> Optional[PersonaConfig]:
        """Returns the currently active persona configuration."""
        return self._active_persona

    def list_personas(self) -> List[str]:
        """Lists the names of available personas."""
        try:
            return self._persona_loader.list_available()
        except Exception as e:
             self.logger.exception("Failed to list available personas.")
             return []

    def _apply_persona_to_history(self):
        """Adds or updates the system message in history based on the active persona."""
        if not self._active_persona or not self._active_persona.system_prompt:
            self.logger.debug("No active persona or system prompt to apply to history.")
            return

        history = self._history_manager.get_history()
        system_prompt_content = self._active_persona.system_prompt

        if history and history[0].role == 'system':
            # Replace existing system prompt if it's different
            if history[0].content != system_prompt_content:
                 # Create a new message to ensure immutability if Message is frozen
                 new_system_message = Message(role='system', content=system_prompt_content)
                 history[0] = new_system_message
                 self._history_manager.set_history(history) # Update history manager
                 self.logger.debug("Updated system prompt in history.")
            else:
                 self.logger.debug("System prompt in history already matches active persona.")
        elif not history:
            # Add system prompt if history is empty
            sys_msg = Message(role='system', content=system_prompt_content)
            # Use history manager's method to add the message
            self._history_manager.add_message(sys_msg)
            self.logger.debug("Added system prompt to history.")
        else:
             # History exists but doesn't start with a system message. Insert one?
             # Design Decision: For now, only add/update if history is empty or starts with system.
             self.logger.debug("History exists but doesn't start with a system message. Not adding persona prompt.")

    # --- Overrides ---
    def set_override(self, key: str, value: Any) -> None:
        """Sets a temporary override for LLM parameters (e.g., 'model', 'temperature')."""
        self.logger.debug(f"Setting instance override: {key}={value}")
        self._instance_overrides[key] = value

    def remove_override(self, key: str) -> None:
        """Removes a specific override."""
        if key in self._instance_overrides:
            self.logger.debug(f"Removing instance override: {key}")
            del self._instance_overrides[key]

    def clear_overrides(self) -> None:
        """Clears all instance-level overrides."""
        self.logger.debug("Clearing all instance overrides.")
        self._instance_overrides = {}

    def get_overrides(self) -> Dict[str, Any]:
        """Returns the current instance overrides."""
        return self._instance_overrides.copy()

    # --- Snippets ---
    def add_snippet(self, name: str, role: Literal['user', 'assistant', 'system'] = 'user') -> bool:
        """Adds content from a snippet to the history."""
        self.logger.debug(f"Attempting to add snippet '{name}' as role '{role}'.")
        try:
            content = self._snippet_provider.get(name)
            exec_count, cell_id = self._get_current_context()
            msg = Message(
                role=role,
                content=content,
                execution_count=exec_count,
                cell_id=cell_id, # Associate with the current cell run
                metadata={"source": f"snippet:{name}"}
            )
            self._history_manager.add_message(msg)
            self.logger.info(f"Added snippet '{name}' as role '{role}'")
            return True
        except ResourceNotFoundError as e:
            self.logger.error(f"Failed to add snippet: {e}")
            # Optionally raise SnippetError here instead of returning False
            raise SnippetError(f"Snippet '{name}' not found.") from e
        except Exception as e:
             self.logger.exception(f"An unexpected error occurred while adding snippet '{name}'.")
             raise SnippetError(f"Failed to process snippet '{name}': {e}") from e

    def list_snippets(self) -> List[str]:
         """Lists the names of available snippets."""
         try:
            return self._snippet_provider.list_available()
         except Exception as e:
              self.logger.exception("Failed to list available snippets.")
              return []

    # --- Core Interaction ---
    async def send_message(
        self,
        prompt: str,
        *, # Force keyword arguments after prompt
        persona_name: Optional[str] = None, # Option to use a specific persona for this call only
        stream_handler: Optional[StreamCallbackHandler] = None,
        add_to_history: bool = True,
        auto_rollback: bool = True, # Automatically rollback on cell rerun?
        **runtime_llm_params: Any # e.g., temperature, max_tokens passed directly for this call
    ) -> Optional[Message]: # Returns the assistant's message object, or None if streaming handled entirely by callbacks
        """
        Handles sending a user prompt, managing history, and interacting with the LLM.

        Args:
            prompt: The user's input text.
            persona_name: Temporarily use this persona instead of the active one.
            stream_handler: An object handling streaming callbacks. If None, non-streaming mode.
            add_to_history: Whether to add the user prompt and assistant response to history.
            auto_rollback: If True, check context provider for cell rerun and rollback history.
            **runtime_llm_params: Ad-hoc LLM parameters for this specific call.

        Returns:
            The assistant's Message object if not streaming or if handler doesn't fully consume it.
            None if streaming and handled by the callback handler.

        Raises:
            ConfigurationError: If no model is specified.
            LLMInteractionError: If the API call fails.
            HistoryManagementError: If history cannot be managed correctly.
            SnippetError: If adding a snippet fails.
        """
        exec_count, cell_id = self._get_current_context()
        self.logger.info(f"Processing send_message request (Exec: {exec_count}, Cell: {cell_id[-8:] if cell_id else 'N/A'}).")

        # 1. Handle Auto-Rollback
        if auto_rollback and cell_id:
            try:
                rolled_back = self._history_manager.rollback_to_cell(cell_id)
                if rolled_back:
                    self.logger.info(f"Cell rerun detected (ID: ...{cell_id[-8:]}). History rolled back.")
            except Exception as e:
                 # Log rollback failure but attempt to continue
                 self.logger.exception(f"Error during auto-rollback for cell_id '{cell_id[-8:]}'. Proceeding cautiously.")
                 # Re-raise if rollback is critical? For now, log and continue.
                 # raise HistoryManagementError(f"Rollback failed for cell {cell_id}") from e

        # 2. Prepare User Message
        user_message = Message(role='user', content=prompt, execution_count=exec_count, cell_id=cell_id)
        if add_to_history:
            try:
                self._history_manager.add_message(user_message) # Add user message before LLM call
            except Exception as e:
                 self.logger.exception("Failed to add user message to history.")
                 raise HistoryManagementError("Failed to add user message.") from e

        # 3. Determine Effective Configuration
        target_persona = self._active_persona
        if persona_name:
            self.logger.debug(f"Attempting to use temporary persona '{persona_name}' for this call.")
            try:
                target_persona = self._persona_loader.load(persona_name)
            except ResourceNotFoundError:
                self.logger.warning(f"Temporary persona '{persona_name}' not found, using active session persona if available.")
                # Fall back to active persona (which might be None)
            except Exception as e:
                 self.logger.exception(f"Failed loading temporary persona '{persona_name}', using active session persona.")

        llm_config = self._resolve_llm_config(target_persona, runtime_llm_params)
        model_name = llm_config.pop('model', None) # Pop model, it's passed separately
        if not model_name:
             # Try getting model from overrides if not in resolved config (e.g., from persona)
             model_name = self._instance_overrides.get('model', self.settings.default_model_name)

        if not model_name:
            # If still no model, revert history if added, then raise error
            if add_to_history: self._history_manager.revert_last_turn()
            raise ConfigurationError("No LLM model specified via persona, overrides, runtime params, or default settings.")

        # 4. Prepare messages for LLM
        try:
            history_for_llm = [msg.to_llm_format() for msg in self._history_manager.get_history()]
        except Exception as e:
             self.logger.exception("Failed to format history for LLM.")
             if add_to_history: self._history_manager.revert_last_turn()
             raise HistoryManagementError("Failed to format history.") from e

        # 5. Call LLM Client
        self.logger.info(f"Sending {len(history_for_llm)} messages to model '{model_name}' (stream={stream_handler is not None}). Params: {llm_config}")
        assistant_response_content = None
        llm_metadata = {} # To store metadata from the response if available

        try:
            response_or_generator = await self._llm_client.chat_completion(
                messages=history_for_llm,
                model=model_name,
                stream=(stream_handler is not None),
                **llm_config
            )
            # --- TODO: Extract token counts and other metadata from response_or_generator ---
            # This depends heavily on the structure returned by the LLMClientInterface implementation (LiteLLM)
            # Example placeholder:
            # if not stream_handler and hasattr(response_or_generator, 'usage'):
            #     llm_metadata['token_usage'] = response_or_generator.usage.dict() # Example structure

        except LLMInteractionError as e:
            self.logger.error(f"LLM interaction failed: {e.original_exception or e}")
            if add_to_history: self._history_manager.revert_last_turn() # Remove the user message
            raise # Re-raise the specific error
        except Exception as e:
             self.logger.exception("Unexpected error during LLM client call.")
             if add_to_history: self._history_manager.revert_last_turn()
             raise LLMInteractionError(f"Unexpected LLM client error: {e}", original_exception=e) from e

        # 6. Process Response (Streaming or Non-Streaming)
        assistant_message: Optional[Message] = None
        stream_error_occurred = False

        if stream_handler:
            try:
                stream_handler.on_stream_start()
                full_response = ""
                async for chunk in response_or_generator: # Assuming LiteLLM async generator yields delta content
                    # --- TODO: Adapt based on actual structure yielded by LiteLLM's stream ---
                    # Example assuming chunk is similar to OpenAI's streaming chunk
                    try:
                        delta_content = chunk.choices[0].delta.content or ""
                        if delta_content:
                            full_response += delta_content
                            stream_handler.on_stream_chunk(delta_content)
                        # Check for finish reason, token counts in final chunk?
                        # if chunk.choices[0].finish_reason:
                        #     llm_metadata['finish_reason'] = chunk.choices[0].finish_reason
                        # if hasattr(chunk, 'usage'): # Usage might appear in the last chunk
                        #     llm_metadata['token_usage'] = chunk.usage.dict()
                    except (AttributeError, IndexError, TypeError) as chunk_error:
                         self.logger.warning(f"Could not parse stream chunk: {chunk_error}. Chunk: {chunk}")
                         # Decide whether to continue or raise

                assistant_response_content = full_response
                stream_handler.on_stream_end(full_response)
                self.logger.info(f"Streaming finished. Full response length: {len(full_response)}")

            except Exception as e:
                stream_error_occurred = True
                err = LLMInteractionError(f"Error processing LLM stream: {e}", original_exception=e)
                self.logger.exception("Error during stream processing.")
                try:
                     stream_handler.on_stream_error(err)
                except Exception as handler_err:
                     self.logger.error(f"Stream handler's on_stream_error failed: {handler_err}")

                # Decide if partial history should be kept or user message reverted
                if add_to_history:
                     self.logger.warning("Reverting user message due to stream processing error.")
                     self._history_manager.revert_last_turn()
                raise err from e # Propagate error

        else: # Non-streaming
            try:
                # --- TODO: Adapt based on actual structure of non-streaming response from LiteLLM ---
                # Example assuming OpenAI-like structure
                assistant_response_content = response_or_generator.choices[0].message.content
                # if hasattr(response_or_generator, 'usage'):
                #     llm_metadata['token_usage'] = response_or_generator.usage.dict()
                # llm_metadata['finish_reason'] = response_or_generator.choices[0].finish_reason
                self.logger.info(f"Received non-streaming response. Length: {len(assistant_response_content)}")
            except (AttributeError, IndexError, TypeError) as e:
                 err = LLMInteractionError(f"Unexpected LLM response format: {response_or_generator}", original_exception=e)
                 self.logger.error(f"Failed to parse non-streaming response: {err}")
                 if add_to_history: self._history_manager.revert_last_turn()
                 raise err from e

        # 7. Finalize History (if applicable and no stream error)
        if add_to_history and assistant_response_content is not None and not stream_error_occurred:
            try:
                final_metadata = {"model_used": model_name}
                # final_metadata.update(llm_metadata) # Add token counts etc. if extracted

                assistant_message = Message(
                    role='assistant',
                    content=assistant_response_content,
                    execution_count=exec_count, # Associate with same cell run
                    cell_id=cell_id,
                    metadata=final_metadata
                )
                self._history_manager.add_message(assistant_message)
                self.logger.debug(f"Assistant response added to history (ID: {assistant_message.id}).")
            except Exception as e:
                 self.logger.exception("Failed to add assistant message to history.")
                 # Don't raise here, as the core interaction succeeded, but log failure.
                 # Consider if this state requires specific handling.

        # Return the message object unless streaming handled everything
        return assistant_message if not stream_handler else None

    def _resolve_llm_config(self, persona: Optional[PersonaConfig], runtime_params: Dict[str, Any]) -> Dict[str, Any]:
        """Merges config from persona, instance overrides, and runtime params."""
        config: Dict[str, Any] = {}
        # Order of precedence: Runtime > Instance Overrides > Persona > Defaults (handled in client)
        if persona and persona.llm_params:
            config.update(persona.llm_params)
            self.logger.debug(f"Applied persona params: {persona.llm_params}")
        if self._instance_overrides:
             config.update(self._instance_overrides)
             self.logger.debug(f"Applied instance overrides: {self._instance_overrides}")
        if runtime_params:
             config.update(runtime_params)
             self.logger.debug(f"Applied runtime params: {runtime_params}")

        # Log effective config (mask secrets if necessary, though API key is handled separately)
        self.logger.debug(f"Resolved LLM config for call: {config}")
        return config

    def _get_current_context(self) -> Tuple[Optional[int], Optional[str]]:
        """Gets context identifiers using the injected provider."""
        if self._context_provider:
            try:
                return self._context_provider.get_current_context()
            except Exception as e:
                self.logger.warning(f"Context provider failed: {e}", exc_info=False) # Keep log concise
        return None, None

    # --- History Access & Manipulation ---
    def get_history(self) -> List[Message]:
        """Gets a copy of the current conversation history."""
        return self._history_manager.get_history()

    def clear_history(self) -> None:
        """Clears the current session's history and reapplies persona system prompt."""
        self._history_manager.clear()
        self._apply_persona_to_history() # Re-add system prompt if needed
        self.logger.info("History cleared and persona prompt reapplied (if applicable).")

    def revert_last_turn(self) -> None:
        """Removes the last user/assistant turn from history."""
        # Uses HistoryManager's implementation
        self._history_manager.revert_last_turn()
        # Logged within HistoryManager

    # --- Session Persistence ---
    def save_session(self, identifier: Optional[str] = None) -> str:
        """Saves the current session history using the HistoryStore."""
        save_id = identifier or self._session_id
        self.logger.info(f"Attempting to save session with ID: {save_id}")
        current_history = self._history_manager.get_history()
        metadata = ConversationMetadata(
            session_id=save_id,
            saved_at=datetime.utcnow(),
            persona_name=self._active_persona.name if self._active_persona else None,
            message_count=len(current_history),
            initial_settings={ # Save relevant initial config at time of save
                 'default_model_name': self.settings.default_model_name,
                 'active_persona_name': self._active_persona.name if self._active_persona else None,
                 'instance_overrides': self._instance_overrides.copy() # Save overrides active at save time
            }
            # custom_tags could be added via another method later
        )
        try:
            save_path = self._history_store.save(current_history, metadata)
            self._session_id = save_id # Update session ID if saved under a new name/ID
            self.logger.info(f"Session '{save_id}' saved successfully: {save_path}")
            return save_path
        except Exception as e:
            self.logger.exception(f"Failed to save session '{save_id}'.")
            raise PersistenceError(f"Failed to save session '{save_id}': {e}") from e

    def load_session(self, identifier: str) -> None:
        """Loads a session history using the HistoryStore."""
        self.logger.info(f"Attempting to load session with ID: {identifier}")
        try:
            messages, metadata = self._history_store.load(identifier)
            self._history_manager.set_history(messages)
            self._session_id = identifier # Update manager's session ID
            self.logger.info(f"Session '{identifier}' loaded successfully with {len(messages)} messages.")

            # Attempt to restore persona based on saved metadata
            if metadata.persona_name:
                 self.logger.debug(f"Attempting to restore persona '{metadata.persona_name}' from loaded session.")
                 try:
                     self.select_persona(metadata.persona_name)
                 except ResourceNotFoundError:
                      self.logger.warning(f"Persona '{metadata.persona_name}' from loaded session not found. Current persona remains unchanged.")
                 except Exception as e:
                      self.logger.error(f"Error restoring persona '{metadata.persona_name}' from loaded session: {e}")
            else:
                 # If no persona saved, maybe clear the current one? Or keep it?
                 # Design decision: Keep current manager state unless explicitly loaded.
                 self.logger.debug("No persona name found in loaded session metadata.")

            # Restore overrides? Design decision: Overrides are typically transient.
            # Loading overrides might be confusing. Log if they existed.
            if metadata.initial_settings.get('instance_overrides'):
                 self.logger.info(f"Loaded session had overrides at save time: {metadata.initial_settings['instance_overrides']}. They are NOT automatically reapplied.")

        except ResourceNotFoundError as e:
             self.logger.error(f"Failed to load session: {e}")
             raise # Re-raise specific error
        except Exception as e:
            self.logger.exception(f"Failed to load session '{identifier}'.")
            raise PersistenceError(f"Failed to load session '{identifier}': {e}") from e

    def list_saved_sessions(self) -> List[str]:
         """Lists identifiers of saved sessions available via the HistoryStore."""
         try:
            if hasattr(self._history_store, 'list_saved'):
                 return self._history_store.list_saved()
            else:
                 self.logger.warning("The configured HistoryStore does not support listing saved sessions.")
                 return []
         except Exception as e:
              self.logger.exception("Failed to list saved sessions.")
              return []

    def _generate_session_id(self) -> str:
        """Generates a unique ID for a new session."""
        # Simple timestamp-based ID for default file saving
        return f"chat_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # --- Optional Features ---
    def export_history_to_df(self) -> Any: # Return type Any to avoid hard pandas dependency
        """Exports history to a Pandas DataFrame (requires pandas)."""
        self.logger.debug("Attempting to export history to DataFrame.")
        try:
            import pandas as pd
            history_dicts = [msg.model_dump() for msg in self._history_manager.get_history()]
            df = pd.DataFrame(history_dicts)
            self.logger.info(f"History exported to DataFrame with {len(df)} rows.")
            return df
        except ImportError:
            self.logger.error("Pandas library is required for DataFrame export.")
            raise ImportError("Please install pandas to use this feature: `pip install 'cellmage[pandas]'` or `poetry install --extras pandas`") from None
        except Exception as e:
            self.logger.exception("Failed to export history to DataFrame.")
            raise

    async def discover_models(self) -> List[Dict[str, Any]]:
         """Discovers available models via the LLM client."""
         self.logger.debug("Attempting to discover available models.")
         try:
             if hasattr(self._llm_client, 'get_available_models'):
                  models = await self._llm_client.get_available_models()
                  self.logger.info(f"Discovered {len(models)} potential models.")
                  return models
             else:
                  self.logger.warning("The configured LLM client does not support model discovery.")
                  return []
         except LLMInteractionError as e:
              self.logger.error(f"Model discovery failed via LLM client: {e}")
              return []
         except Exception as e:
              self.logger.exception("Unexpected error during model discovery.")
              return []

