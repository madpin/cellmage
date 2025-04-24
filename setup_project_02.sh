#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
# set -u # Optional: uncomment if you want stricter variable checking
# Ensure pipeline failures are reported
set -o pipefail

echo "🚀 Populating Python files with architectural boilerplate..."

# Define the base source directory
SRC_BASE="cellmage/src/notebook_llm"

# --- Populate config.py ---
echo "Populating ${SRC_BASE}/config.py..."
cat << 'EOF' > "${SRC_BASE}/config.py"
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import DirectoryPath, Field, HttpUrl
from typing import Optional
import warnings
from pathlib import Path

class Settings(BaseSettings):
    """Manages application settings via environment variables, .env file, or defaults."""
    api_key: Optional[str] = Field(None, validation_alias='NBLLM_API_KEY')
    api_base: Optional[str] = Field(None, validation_alias='NBLLM_API_BASE') # Changed to str to avoid early validation issues if URL is complex/local
    log_level: str = Field("INFO", validation_alias='NBLLM_LOG_LEVEL')
    personas_dir: Path = Field("llm_personas", validation_alias='NBLLM_PERSONAS_DIR')
    save_dir: Path = Field("llm_conversations", validation_alias='NBLLM_SAVE_DIR')
    snippets_dir: Path = Field("snippets", validation_alias='NBLLM_SNIPPETS_DIR')

    # Default model to use if not specified by persona, override, or call
    default_model_name: Optional[str] = Field(None, validation_alias='NBLLM_DEFAULT_MODEL')

    # Configuration for Pydantic Settings
    model_config = SettingsConfigDict(
        env_file='.env',          # Load .env file if present
        env_file_encoding='utf-8',
        extra='ignore'            # Ignore extra fields from env/file
    )

# Singleton instance, loaded once on import
try:
    settings = Settings()

    # Create directories if they don't exist after loading settings
    settings.personas_dir.mkdir(parents=True, exist_ok=True)
    settings.save_dir.mkdir(parents=True, exist_ok=True)
    settings.snippets_dir.mkdir(parents=True, exist_ok=True)

except Exception as e:
    warnings.warn(f"Could not automatically create settings directories: {e}")
    # Allow execution to continue, components should handle missing dirs later if needed
    settings = Settings() # Load again to have a default object

EOF

# --- Populate models.py ---
echo "Populating ${SRC_BASE}/models.py..."
cat << 'EOF' > "${SRC_BASE}/models.py"
import uuid
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class Message(BaseModel):
    """Represents a single message in the conversation history."""
    role: Literal['system', 'user', 'assistant']
    content: str
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    execution_count: Optional[int] = None # Environment-specific metadata
    cell_id: Optional[str] = None         # Environment-specific metadata
    metadata: Dict[str, Any] = Field(default_factory=dict) # For future extensibility

    def to_llm_format(self) -> Dict[str, str]:
        """Converts message to the format expected by LLM clients (e.g., OpenAI)."""
        # Basic format, might need adjustment based on specific LLM client needs
        return {"role": self.role, "content": self.content}

class PersonaConfig(BaseModel):
    """Configuration loaded from a personality resource."""
    name: str # Typically derived from the resource name/file name
    system_prompt: str
    llm_params: Dict[str, Any] = Field(default_factory=dict) # e.g., model, temperature
    source_path: Optional[str] = None # Path to the original file, if applicable

class ConversationMetadata(BaseModel):
    """Metadata saved with a conversation history."""
    session_id: str
    saved_at: datetime
    persona_name: Optional[str]
    initial_settings: Dict[str, Any] # Snapshot of relevant settings at save time
    message_count: int
    custom_tags: Dict[str, str] = Field(default_factory=dict)

EOF

# --- Populate exceptions.py ---
echo "Populating ${SRC_BASE}/exceptions.py..."
cat << 'EOF' > "${SRC_BASE}/exceptions.py"
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
EOF

# --- Populate interfaces.py ---
echo "Populating ${SRC_BASE}/interfaces.py..."
cat << 'EOF' > "${SRC_BASE}/interfaces.py"
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
EOF

# --- Populate history_manager.py ---
echo "Populating ${SRC_BASE}/history_manager.py..."
cat << 'EOF' > "${SRC_BASE}/history_manager.py"
from typing import List, Optional, Tuple, Dict
from .models import Message
from .exceptions import HistoryManagementError
import logging

logger = logging.getLogger(__name__)

class HistoryManager:
    """Manages the in-memory list of messages for a session, including rollback logic."""
    _messages: List[Message]
    _cell_tracking: Dict[str, int] # Maps cell_id -> index of *last* message added by that cell

    def __init__(self, initial_messages: Optional[List[Message]] = None):
        """Initializes the history manager."""
        self._messages = initial_messages or []
        self._cell_tracking = {}
        self._rebuild_tracking()
        logger.debug(f"HistoryManager initialized with {len(self._messages)} messages.")

    def add_message(self, message: Message):
        """Adds a single message and updates cell tracking if applicable."""
        if not isinstance(message, Message):
            raise TypeError("Can only add Message objects to history.")
        self._messages.append(message)
        if message.cell_id:
            self._cell_tracking[message.cell_id] = len(self._messages) - 1
        logger.debug(f"Added message (Role: {message.role}, Cell: {message.cell_id})")

    def add_messages(self, messages: List[Message]):
        """Adds multiple messages sequentially."""
        for msg in messages:
            self.add_message(msg) # Ensures tracking is updated per message

    def get_history(self) -> List[Message]:
        """Returns a shallow copy of the current message history."""
        return self._messages[:]

    def set_history(self, messages: List[Message]):
        """
        Replaces the entire history and rebuilds tracking.
        Use with caution, as it bypasses normal addition logic.
        """
        if not all(isinstance(m, Message) for m in messages):
             raise TypeError("Can only set history with a list of Message objects.")
        self._messages = messages
        self._rebuild_tracking()
        logger.info(f"History explicitly set with {len(self._messages)} messages.")

    def clear(self):
        """Clears all messages and tracking information."""
        self._messages = []
        self._cell_tracking = {}
        logger.info("History cleared.")

    def revert_last_turn(self):
        """
        Removes the last user/assistant pair (or single message if history ends unexpectedly).
        Primarily intended for error recovery during LLM calls.
        """
        if not self._messages:
            logger.debug("Attempted to revert last turn, but history is empty.")
            return

        # Simple revert strategy: remove last 2 if user/assistant pair, else last 1
        count_to_remove = 0
        if len(self._messages) >= 2:
            if self._messages[-2].role == 'user' and self._messages[-1].role == 'assistant':
                count_to_remove = 2
            else:
                count_to_remove = 1 # Unexpected end, remove just the last one
        elif len(self._messages) == 1:
             count_to_remove = 1

        if count_to_remove > 0:
            self._messages = self._messages[:-count_to_remove]
            self._rebuild_tracking() # Easiest way to keep tracking consistent
            logger.info(f"Reverted last {count_to_remove} message(s).")
        else:
            logger.debug("Did not revert messages (no clear user/assistant pair at end).")

    def rollback_to_cell(self, cell_id: str) -> bool:
        """
        Removes history entries associated with the specified cell_id and any subsequent entries.
        This handles the case where a cell is re-executed in a notebook.

        Returns:
            bool: True if a rollback occurred (messages were removed), False otherwise.
        """
        if not cell_id:
            logger.debug("Rollback requested with no cell_id, ignoring.")
            return False

        if cell_id not in self._cell_tracking:
            logger.debug(f"Rollback requested for cell_id '{cell_id[-8:]}', but not found in tracking.")
            return False # Cell ID never added messages or was already rolled back

        last_index_for_cell = self._cell_tracking[cell_id]
        logger.debug(f"Found cell_id '{cell_id[-8:]}' last contributing at index {last_index_for_cell}.")

        # We need to find the index of the *first* message added by this specific cell run.
        # This is tricky because a cell might add multiple messages (user prompt, snippet, assistant response).
        # We iterate backwards from the *last* known index for this cell.
        first_index_for_cell = -1
        for i in range(last_index_for_cell, -1, -1):
            if self._messages[i].cell_id == cell_id:
                first_index_for_cell = i
            elif self._messages[i].cell_id != cell_id:
                # We've gone past the messages for this cell run.
                break
        else:
            # If the loop finishes without break, it means all messages from the start
            # were from this cell (or first_index_for_cell is still -1 if something weird happened).
            if first_index_for_cell == -1: # Should not happen if cell_id is in tracking
                 logger.warning(f"Inconsistent state during rollback for cell_id '{cell_id[-8:]}'.")
                 return False

        rollback_point = first_index_for_cell
        if rollback_point < len(self._messages):
            num_removed = len(self._messages) - rollback_point
            self._messages = self._messages[:rollback_point]
            self._rebuild_tracking() # Rebuild tracking after modification
            logger.info(f"Rolled back {num_removed} message(s) due to cell_id '{cell_id[-8:]}'. New history length: {len(self._messages)}.")
            return True
        else:
            # This case means the cell was the very last thing, and no messages followed.
            # Technically no rollback needed, but log for clarity.
            logger.debug(f"Cell_id '{cell_id[-8:]}' was the last contributor, no subsequent messages to roll back.")
            return False

    def _rebuild_tracking(self):
        """Internal helper to rebuild the cell_id -> last_index mapping."""
        self._cell_tracking = {}
        for i, msg in enumerate(self._messages):
            if msg.cell_id:
                # Store the latest index found for each cell_id
                self._cell_tracking[msg.cell_id] = i
        logger.debug(f"Cell tracking rebuilt. Tracking {len(self._cell_tracking)} unique cell IDs.")

EOF

# --- Populate chat_manager.py ---
echo "Populating ${SRC_BASE}/chat_manager.py..."
cat << 'EOF' > "${SRC_BASE}/chat_manager.py"
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

EOF

# --- Populate adapters/llm_client.py ---
echo "Populating ${SRC_BASE}/adapters/llm_client.py..."
cat << 'EOF' > "${SRC_BASE}/adapters/llm_client.py"
import litellm
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging

from ..interfaces import LLMClientInterface
from ..exceptions import LLMInteractionError, ConfigurationError
from ..config import settings # Access configured API key/base if needed

logger = logging.getLogger(__name__)

# Configure LiteLLM logging based on application settings
# Note: LiteLLM's logging might be configured globally. Be mindful of side effects.
# litellm.set_verbose = settings.log_level in ["DEBUG"] # Example basic mapping

class LiteLLMAdapter(LLMClientInterface):
    """Adapter implementing LLMClientInterface using the LiteLLM library."""

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        stream: bool = False,
        api_key: Optional[str] = None, # Allow overriding config
        api_base: Optional[str] = None, # Allow overriding config
        **kwargs: Any
    ) -> Any: # Returns ModelResponse or AsyncGenerator[ModelChunk]
        """Sends messages via LiteLLM, handling potential overrides and errors."""
        effective_api_key = api_key if api_key is not None else settings.api_key
        effective_api_base = str(api_base) if api_base is not None else str(settings.api_base) if settings.api_base else None

        if not model:
             # This should ideally be caught earlier in ChatManager
             logger.error("LLM model name is required but was not provided to the adapter.")
             raise ConfigurationError("LLM model name is required.")

        call_args = {
            "model": model,
            "messages": messages,
            "api_key": effective_api_key or None, # Ensure None if empty string
            "api_base": effective_api_base or None,
            "stream": stream,
            **kwargs # Pass through other params like temperature, max_tokens
        }
        # Remove None values for cleaner calls, LiteLLM might handle them anyway
        call_args = {k: v for k, v in call_args.items() if v is not None}

        logger.debug(f"Calling LiteLLM acompletion with args: {{'model': '{model}', 'stream': {stream}, 'num_messages': {len(messages)}}}") # Avoid logging messages/key
        try:
            # litellm.acompletion handles both stream=True/False
            response = await litellm.acompletion(**call_args)
            logger.debug(f"LiteLLM acompletion call successful for model '{model}'.")
            return response # Returns ModelResponse or AsyncGenerator
        except litellm.exceptions.AuthenticationError as e:
             logger.error(f"LiteLLM AuthenticationError for model '{model}': {e}")
             raise LLMInteractionError(f"Authentication failed for model '{model}'. Check API key/base.", original_exception=e) from e
        except litellm.exceptions.RateLimitError as e:
             logger.warning(f"LiteLLM RateLimitError for model '{model}': {e}")
             raise LLMInteractionError(f"Rate limit exceeded for model '{model}'.", original_exception=e) from e
        except litellm.exceptions.NotFound as e:
             logger.error(f"LiteLLM NotFound Error (check model name/API base): {e}")
             raise LLMInteractionError(f"Model '{model}' not found or API endpoint invalid.", original_exception=e) from e
        except Exception as e:
            # Catch generic exceptions from LiteLLM or network issues
            logger.exception(f"An unexpected error occurred during LiteLLM call for model '{model}'.")
            raise LLMInteractionError(f"LiteLLM API call failed unexpectedly: {e}", original_exception=e) from e

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Uses litellm.model_list (requires appropriate credentials often)."""
        logger.debug("Attempting to fetch available models via litellm.model_list.")
        try:
            # Note: model_list might need credentials passed explicitly depending on provider
            # LiteLLM attempts to use environment variables if not passed.
            # This might require requests library or direct API calls for some endpoints if litellm fails.
            model_list = await litellm.model_list()
            logger.info(f"Successfully retrieved model list via LiteLLM, found {len(model_list)} entries.")
            # The structure of returned dicts varies by provider via LiteLLM
            return model_list
        except Exception as e:
            logger.exception("Failed to retrieve model list via LiteLLM.")
            # Don't raise LLMInteractionError here? Or maybe do?
            # For now, log and return empty, as this is often optional.
            return []

EOF

# --- Populate resources/file_loader.py ---
echo "Populating ${SRC_BASE}/resources/file_loader.py..."
cat << 'EOF' > "${SRC_BASE}/resources/file_loader.py"
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging
import re

from ..interfaces import PersonaLoader, SnippetProvider
from ..models import PersonaConfig
from ..exceptions import ResourceNotFoundError, ConfigurationError

logger = logging.getLogger(__name__)

# Regex to find YAML frontmatter
YAML_FRONT_MATTER_REGEX = re.compile(r"^\s*---\s*\n(.*?\n?)\s*---\s*\n", re.DOTALL | re.MULTILINE)

def _parse_markdown_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extracts YAML frontmatter and main content from markdown text."""
    match = YAML_FRONT_MATTER_REGEX.match(content)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter, dict):
                frontmatter = {} # Ignore if YAML is not a dictionary
            main_content = content[match.end():].strip()
            return frontmatter, main_content
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}. Treating as plain text.")
            # Fall through to return empty frontmatter and original content
    return {}, content.strip() # No frontmatter found or parse error

class FileLoader(PersonaLoader, SnippetProvider):
    """Loads Personas and Snippets from files in specified directories."""

    def __init__(self, personas_base_dir: Path, snippets_base_dir: Path):
        """
        Initializes the FileLoader.

        Args:
            personas_base_dir: The directory containing persona markdown files.
            snippets_base_dir: The directory containing snippet files (markdown or text).
        """
        self.personas_dir = Path(personas_base_dir)
        self.snippets_dir = Path(snippets_base_dir)

        if not self.personas_dir.is_dir():
            logger.warning(f"Personas directory not found: {self.personas_dir}. Creating it.")
            self.personas_dir.mkdir(parents=True, exist_ok=True) # Attempt to create
            # raise ConfigurationError(f"Personas directory not found: {self.personas_dir}")

        if not self.snippets_dir.is_dir():
            logger.warning(f"Snippets directory not found: {self.snippets_dir}. Creating it.")
            self.snippets_dir.mkdir(parents=True, exist_ok=True) # Attempt to create
            # raise ConfigurationError(f"Snippets directory not found: {self.snippets_dir}")

        logger.info(f"FileLoader initialized. Personas: '{self.personas_dir}', Snippets: '{self.snippets_dir}'")

    # --- PersonaLoader Implementation ---

    def load(self, name: str) -> PersonaConfig:
        """
        Loads a persona from a markdown file.
        The filename (without extension) is used as the name.
        YAML frontmatter provides llm_params, the rest is the system_prompt.
        """
        persona_path = self.personas_dir / f"{name}.md"
        logger.debug(f"Attempting to load persona '{name}' from {persona_path}")

        if not persona_path.is_file():
            raise ResourceNotFoundError("persona", name)

        try:
            content = persona_path.read_text(encoding='utf-8')
            frontmatter, system_prompt = _parse_markdown_frontmatter(content)

            # Ensure system_prompt is not None if file is empty after frontmatter
            system_prompt = system_prompt or ""

            # Basic validation (can be expanded)
            if not isinstance(frontmatter, dict):
                 logger.warning(f"Invalid frontmatter format in {persona_path}, expected dict, got {type(frontmatter)}. Ignoring params.")
                 frontmatter = {}

            persona_config = PersonaConfig(
                name=name,
                system_prompt=system_prompt,
                llm_params=frontmatter, # Pass the whole dict
                source_path=str(persona_path)
            )
            logger.info(f"Successfully loaded persona '{name}'.")
            return persona_config

        except FileNotFoundError: # Should be caught by is_file() check, but defensive
             raise ResourceNotFoundError("persona", name) from None
        except Exception as e:
            logger.exception(f"Failed to load or parse persona file: {persona_path}")
            raise ConfigurationError(f"Error loading persona '{name}': {e}") from e

    def list_available(self) -> List[str]:
        """Lists available persona names (markdown filenames without extension)."""
        if not self.personas_dir.exists():
             logger.warning(f"Cannot list personas, directory does not exist: {self.personas_dir}")
             return []
        try:
            return sorted([p.stem for p in self.personas_dir.glob("*.md") if p.is_file()])
        except Exception as e:
             logger.exception(f"Failed to list files in personas directory: {self.personas_dir}")
             return []

    # --- SnippetProvider Implementation ---

    def get(self, name: str) -> str:
        """
        Gets the content of a snippet file. Tries .md then .txt extension.
        """
        snippet_path_md = self.snippets_dir / f"{name}.md"
        snippet_path_txt = self.snippets_dir / f"{name}.txt"
        snippet_path = None

        if snippet_path_md.is_file():
             snippet_path = snippet_path_md
        elif snippet_path_txt.is_file():
             snippet_path = snippet_path_txt
        else:
             # Check for name without extension directly
             direct_path = self.snippets_dir / name
             if direct_path.is_file():
                  snippet_path = direct_path
             else:
                  raise ResourceNotFoundError("snippet", name)

        logger.debug(f"Attempting to load snippet '{name}' from {snippet_path}")
        try:
            content = snippet_path.read_text(encoding='utf-8')
            logger.info(f"Successfully loaded snippet '{name}'.")
            return content.strip() # Return stripped content
        except FileNotFoundError: # Defensive
             raise ResourceNotFoundError("snippet", name) from None
        except Exception as e:
            logger.exception(f"Failed to read snippet file: {snippet_path}")
            raise ConfigurationError(f"Error loading snippet '{name}': {e}") from e

    def list_available(self) -> List[str]:
        """Lists available snippet names (filenames without extension)."""
        if not self.snippets_dir.exists():
             logger.warning(f"Cannot list snippets, directory does not exist: {self.snippets_dir}")
             return []
        try:
            # List both .md and .txt files, removing extension
            md_files = {p.stem for p in self.snippets_dir.glob("*.md") if p.is_file()}
            txt_files = {p.stem for p in self.snippets_dir.glob("*.txt") if p.is_file()}
            # Consider listing files without extensions too? For now, stick to .md/.txt
            # other_files = {p.name for p in self.snippets_dir.glob("*") if p.is_file() and not p.suffix in ['.md', '.txt']}
            return sorted(list(md_files.union(txt_files))) # .union(other_files)
        except Exception as e:
             logger.exception(f"Failed to list files in snippets directory: {self.snippets_dir}")
             return []

EOF

# --- Populate storage/markdown_store.py ---
echo "Populating ${SRC_BASE}/storage/markdown_store.py..."
cat << 'EOF' > "${SRC_BASE}/storage/markdown_store.py"
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging
from datetime import datetime

from ..interfaces import HistoryStore
from ..models import Message, ConversationMetadata
from ..exceptions import PersistenceError, ResourceNotFoundError

logger = logging.getLogger(__name__)

# Use the same parser as FileLoader for consistency
from ..resources.file_loader import _parse_markdown_frontmatter, YAML_FRONT_MATTER_REGEX

class MarkdownStore(HistoryStore):
    """Saves and loads conversation history to/from Markdown files with YAML frontmatter."""

    DEFAULT_EXTENSION = ".md"

    def __init__(self, base_dir: Path):
        """
        Initializes the MarkdownStore.

        Args:
            base_dir: The directory where conversation files will be stored.
        """
        self.base_dir = Path(base_dir)
        if not self.base_dir.is_dir():
            logger.warning(f"History storage directory not found: {self.base_dir}. Creating it.")
            self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"MarkdownStore initialized. Storage directory: '{self.base_dir}'")

    def _get_path(self, identifier: str) -> Path:
        """Constructs the full path for a given identifier."""
        # Ensure identifier doesn't contain path traversal characters for security
        safe_identifier = Path(identifier).name
        if not safe_identifier.endswith(self.DEFAULT_EXTENSION):
             safe_identifier += self.DEFAULT_EXTENSION
        return self.base_dir / safe_identifier

    def save(self, messages: List[Message], metadata: ConversationMetadata) -> str:
        """
        Saves the history and metadata to a markdown file.
        Metadata is stored as YAML frontmatter.
        Messages are appended, formatted as markdown blockquotes or similar.
        """
        identifier = metadata.session_id # Use session ID from metadata as filename base
        file_path = self._get_path(identifier)
        logger.debug(f"Attempting to save session '{identifier}' to {file_path}")

        try:
            # Prepare frontmatter (serialize metadata)
            # Exclude session_id as it's used for the filename
            metadata_dict = metadata.model_dump(exclude={'session_id'}, mode='json') # Use 'json' mode for datetime serialization
            frontmatter_yaml = yaml.dump(metadata_dict, default_flow_style=False, sort_keys=False)

            # Prepare message content
            message_content = "\n\n".join(self._format_message_as_markdown(msg) for msg in messages)

            # Combine and write
            full_content = f"---\n{frontmatter_yaml}---\n\n{message_content}\n"

            file_path.write_text(full_content, encoding='utf-8')
            logger.info(f"Successfully saved session '{identifier}' to {file_path}")
            return str(file_path) # Return the actual path saved

        except yaml.YAMLError as e:
             logger.exception(f"Failed to serialize metadata to YAML for session '{identifier}'.")
             raise PersistenceError(f"YAML serialization error saving '{identifier}': {e}") from e
        except IOError as e:
             logger.exception(f"Failed to write history file: {file_path}")
             raise PersistenceError(f"File write error saving '{identifier}': {e}") from e
        except Exception as e:
             logger.exception(f"An unexpected error occurred while saving session '{identifier}'.")
             raise PersistenceError(f"Unexpected error saving '{identifier}': {e}") from e

    def load(self, identifier: str) -> Tuple[List[Message], ConversationMetadata]:
        """
        Loads history and metadata from a markdown file.
        """
        file_path = self._get_path(identifier)
        logger.debug(f"Attempting to load session '{identifier}' from {file_path}")

        if not file_path.is_file():
            raise ResourceNotFoundError("history", identifier)

        try:
            full_content = file_path.read_text(encoding='utf-8')

            # Parse frontmatter and main content
            frontmatter_dict, message_section = _parse_markdown_frontmatter(full_content)

            # --- TODO: Implement robust parsing of message_section back into Message objects ---
            # This is the complex part. How were messages formatted in _format_message_as_markdown?
            # Need a corresponding parser here.
            # Placeholder: Assume simple parsing for now.
            messages = self._parse_messages_from_markdown(message_section)
            # --- End Placeholder ---

            # Validate and deserialize metadata
            # Add back session_id from the identifier used
            frontmatter_dict['session_id'] = Path(identifier).stem # Use stem to remove suffix if present
            metadata = ConversationMetadata.model_validate(frontmatter_dict)

            logger.info(f"Successfully loaded session '{identifier}' from {file_path}. Found {len(messages)} messages.")
            return messages, metadata

        except FileNotFoundError: # Defensive
             raise ResourceNotFoundError("history", identifier) from None
        except yaml.YAMLError as e:
             logger.exception(f"Failed to parse YAML frontmatter from file: {file_path}")
             raise PersistenceError(f"YAML parsing error loading '{identifier}': {e}") from e
        except Exception as e: # Catches Pydantic validation errors too
            logger.exception(f"Failed to load or parse history file: {file_path}")
            raise PersistenceError(f"Error loading history '{identifier}': {e}") from e

    def list_saved(self) -> List[str]:
        """Lists identifiers (filenames without extension) of saved histories."""
        if not self.base_dir.exists():
             logger.warning(f"Cannot list saved histories, directory does not exist: {self.base_dir}")
             return []
        try:
            # Return the stem (filename without suffix)
            return sorted([p.stem for p in self.base_dir.glob(f"*{self.DEFAULT_EXTENSION}") if p.is_file()])
        except Exception as e:
             logger.exception(f"Failed to list files in history directory: {self.base_dir}")
             return []

    def _format_message_as_markdown(self, message: Message) -> str:
        """Formats a single Message object into a markdown string for saving."""
        # Example format: Role as heading, metadata as details, content as blockquote
        # --- TODO: Finalize a robust and parsable format ---
        metadata_str = f"ID: {message.id} | Timestamp: {message.timestamp.isoformat()} | Cell: {message.cell_id or 'N/A'} | Exec: {message.execution_count or 'N/A'}"
        if message.metadata:
             metadata_str += f" | Meta: {message.metadata}"

        return f"### {message.role.capitalize()}\n`{metadata_str}`\n\n> {message.content.strip()}" # Simple blockquote example

    def _parse_messages_from_markdown(self, markdown_content: str) -> List[Message]:
        """Parses the message section of the markdown file back into Message objects."""
        # --- TODO: Implement the parser corresponding to _format_message_as_markdown ---
        # This needs to reliably split the content back into individual messages
        # and extract role, content, and potentially reconstruct metadata.
        # This is non-trivial if the content itself contains markdown similar to the separators.
        # Using separators like '---' between messages might be more robust.
        logger.warning("_parse_messages_from_markdown is not fully implemented. Returning empty list.")
        messages: List[Message] = []
        # Placeholder logic: Split by headings? Very fragile.
        # parts = re.split(r'\n### (System|User|Assistant)\n', markdown_content)
        # ... complex parsing logic needed ...
        return messages

EOF

# --- Populate resources/memory_loader.py ---
echo "Populating ${SRC_BASE}/resources/memory_loader.py..."
cat << 'EOF' > "${SRC_BASE}/resources/memory_loader.py"
from typing import List, Dict, Any
import logging

from ..interfaces import PersonaLoader, SnippetProvider
from ..models import PersonaConfig
from ..exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)

class MemoryLoader(PersonaLoader, SnippetProvider):
    """In-memory implementation for loading Personas and Snippets, useful for testing."""

    def __init__(
        self,
        personas: Dict[str, PersonaConfig] | None = None,
        snippets: Dict[str, str] | None = None
    ):
        """
        Initializes the MemoryLoader with predefined personas and snippets.

        Args:
            personas: A dictionary mapping persona names to PersonaConfig objects.
            snippets: A dictionary mapping snippet names to their string content.
        """
        self._personas = personas or {}
        self._snippets = snippets or {}
        logger.info(f"MemoryLoader initialized with {len(self._personas)} personas and {len(self._snippets)} snippets.")

    # --- PersonaLoader Implementation ---

    def load(self, name: str) -> PersonaConfig:
        """Loads a persona from the internal dictionary."""
        logger.debug(f"Attempting to load persona '{name}' from memory.")
        if name not in self._personas:
            raise ResourceNotFoundError("persona", name)
        return self._personas[name]

    def list_available(self) -> List[str]:
        """Lists available persona names from the internal dictionary."""
        return sorted(list(self._personas.keys()))

    # --- SnippetProvider Implementation ---

    def get(self, name: str) -> str:
        """Gets the content of a snippet from the internal dictionary."""
        logger.debug(f"Attempting to load snippet '{name}' from memory.")
        if name not in self._snippets:
            raise ResourceNotFoundError("snippet", name)
        return self._snippets[name]

    def list_available(self) -> List[str]:
        """Lists available snippet names from the internal dictionary."""
        return sorted(list(self._snippets.keys()))

    # --- Helper methods for testing ---
    def add_persona(self, persona: PersonaConfig):
        """Adds or updates a persona in memory."""
        self._personas[persona.name] = persona
        logger.debug(f"Added/Updated persona '{persona.name}' in memory.")

    def add_snippet(self, name: str, content: str):
        """Adds or updates a snippet in memory."""
        self._snippets[name] = content
        logger.debug(f"Added/Updated snippet '{name}' in memory.")
EOF

# --- Populate storage/memory_store.py ---
echo "Populating ${SRC_BASE}/storage/memory_store.py..."
cat << 'EOF' > "${SRC_BASE}/storage/memory_store.py"
from typing import List, Dict, Any, Tuple
import logging
from datetime import datetime

from ..interfaces import HistoryStore
from ..models import Message, ConversationMetadata
from ..exceptions import PersistenceError, ResourceNotFoundError

logger = logging.getLogger(__name__)

class MemoryStore(HistoryStore):
    """In-memory implementation for storing/retrieving conversation history, useful for testing."""

    _store: Dict[str, Tuple[List[Message], ConversationMetadata]]

    def __init__(self):
        """Initializes the in-memory store."""
        self._store = {}
        logger.info("MemoryStore initialized.")

    def save(self, messages: List[Message], metadata: ConversationMetadata) -> str:
        """Saves the history and metadata to the internal dictionary."""
        identifier = metadata.session_id
        logger.debug(f"Attempting to save session '{identifier}' to memory.")
        # Store copies to avoid external modification issues
        self._store[identifier] = (
            [msg.model_copy(deep=True) for msg in messages],
            metadata.model_copy(deep=True)
        )
        logger.info(f"Successfully saved session '{identifier}' to memory.")
        return identifier # Return the identifier used

    def load(self, identifier: str) -> Tuple[List[Message], ConversationMetadata]:
        """Loads history and metadata from the internal dictionary."""
        logger.debug(f"Attempting to load session '{identifier}' from memory.")
        if identifier not in self._store:
            raise ResourceNotFoundError("history", identifier)

        # Return copies to prevent modification of the stored data
        messages, metadata = self._store[identifier]
        logger.info(f"Successfully loaded session '{identifier}' from memory.")
        return [msg.model_copy(deep=True) for msg in messages], metadata.model_copy(deep=True)

    def list_saved(self) -> List[str]:
        """Lists identifiers (keys) of saved histories in the store."""
        return sorted(list(self._store.keys()))

    # --- Helper methods for testing ---
    def clear_store(self):
        """Clears all data from the memory store."""
        self._store = {}
        logger.info("Memory store cleared.")

    def get_store_content(self) -> Dict[str, Tuple[List[Message], ConversationMetadata]]:
         """Returns the raw content of the store (primarily for debugging/testing)."""
         return self._store
EOF

# --- Populate integrations/ipython_magic.py ---
echo "Populating ${SRC_BASE}/integrations/ipython_magic.py..."
# NOTE: This is a large file, ensure the heredoc works correctly.
cat << 'EOF' > "${SRC_BASE}/integrations/ipython_magic.py"
# --- Imports ---
import sys
import uuid
import time
import logging
import shlex # For safer parsing of magic line args
from typing import Optional, Tuple, Dict, Any, List

try:
    from IPython import get_ipython
    from IPython.core.magic import Magics, line_magic, cell_magic, magics_class
    from IPython.core.magic_arguments import (
        argument, magic_arguments, parse_argstring, argument_group
    )
    from IPython.display import display, Markdown, HTML, update_display
    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False
    # Define dummy decorators if IPython is not installed, so the file can still be imported
    # This allows checking functionality even without IPython (e.g., basic linting)
    def magics_class(cls): return cls
    def line_magic(func): return func
    def cell_magic(func): return func
    def magic_arguments(): return lambda func: func
    def argument(*args, **kwargs): return lambda func: func
    class Magics: pass # Dummy base class

# --- Project Imports ---
# Use absolute imports relative to the package root
from ..chat_manager import ChatManager
from ..interfaces import ContextProvider, StreamCallbackHandler
from ..exceptions import NotebookLLMError, ResourceNotFoundError, ConfigurationError, LLMInteractionError, PersistenceError
from ..models import Message # For type hints if needed

# --- Logging ---
logger = logging.getLogger(__name__)

# --- Global Instance Management ---
# Global instance (or factory-created) - needs careful management in IPython
# A function to get/create the manager instance is generally safer.
_chat_manager_instance: Optional[ChatManager] = None
_initialization_error: Optional[Exception] = None

def _init_default_manager() -> ChatManager:
    """Initializes the default ChatManager instance using default components."""
    global _initialization_error
    try:
        # Import necessary components dynamically only if needed
        from ..config import settings
        from ..adapters.llm_client import LiteLLMAdapter
        from ..resources.file_loader import FileLoader # Default file-based loaders
        from ..storage.markdown_store import MarkdownStore # Default markdown store

        logger.info("Initializing default ChatManager components...")

        # Create default dependencies
        # Error handling for directory access/creation happens in components now
        loader = FileLoader(settings.personas_dir, settings.snippets_dir)
        store = MarkdownStore(settings.save_dir)
        client = LiteLLMAdapter() # Relies on settings/env vars
        context_provider = IPythonContextProvider() # Provide IPython context

        manager = ChatManager(
            settings=settings,
            llm_client=client,
            persona_loader=loader,
            snippet_provider=loader,
            history_store=store,
            context_provider=context_provider
            # Initial persona/session ID could be loaded from config/env later
        )
        logger.info("Default ChatManager initialized successfully.")
        _initialization_error = None # Clear previous error on success
        return manager
    except Exception as e:
         logger.exception("FATAL: Failed to initialize default NotebookLLM ChatManager.")
         _initialization_error = e # Store the error
         # Re-raise a more user-friendly error for the magic command context
         raise RuntimeError(f"NotebookLLM setup failed. Please check configuration and logs. Error: {e}") from e

def get_chat_manager() -> ChatManager:
    """Gets or creates the singleton ChatManager instance."""
    global _chat_manager_instance
    if _chat_manager_instance is None:
        if _initialization_error:
            # If initialization failed before, raise the stored error
            raise RuntimeError(f"NotebookLLM previously failed to initialize: {_initialization_error}") from _initialization_error
        logger.debug("ChatManager instance not found, attempting initialization.")
        _chat_manager_instance = _init_default_manager() # This might raise RuntimeError

    return _chat_manager_instance

# --- IPython Specific Implementations ---

class IPythonContextProvider(ContextProvider):
    """Provides execution context from the IPython environment."""
    def get_current_context(self) -> Tuple[Optional[int], Optional[str]]:
        """Returns (execution_count, cell_id) if available, else (None, None)."""
        ipython = get_ipython()
        if not ipython or not hasattr(ipython, 'kernel') or not ipython.kernel:
            logger.debug("IPython environment or kernel not available for context.")
            return None, None

        # Safer access to execution_count
        exec_count = getattr(ipython, 'execution_count', None)

        # Cell ID detection logic (refined)
        cell_id: Optional[str] = None
        try:
            # Access parent_header safely
            parent_header = getattr(ipython.kernel.shell, 'parent_header', None)
            if not parent_header or not isinstance(parent_header, dict):
                 logger.debug("Could not retrieve parent_header for cell ID.")
                 return exec_count, None

            # Look in standard metadata locations first
            metadata = parent_header.get("metadata", {})
            if isinstance(metadata, dict):
                # Prioritize known keys
                potential_keys = ["cellId", "vscode_cell_id", "google_colab_cell_id"]
                for key in potential_keys:
                    cell_id = metadata.get(key)
                    if isinstance(cell_id, str) and cell_id: break # Found one
                else: # If loop finishes without break
                    cell_id = None # Ensure cell_id is None if not found in standard keys

                # Check nested metadata structures if not found yet
                if not cell_id and isinstance(metadata.get("metadata"), dict): # General nested
                    for key in potential_keys:
                        cell_id = metadata["metadata"].get(key)
                        if isinstance(cell_id, str) and cell_id: break
                    else: cell_id = None

                if not cell_id and isinstance(metadata.get("colab"), dict): # Colab specific nested
                    cell_id = metadata["colab"].get("cell_id") # More specific key for Colab

            # Fallback for VSCode specific format if still not found
            # Check both header and metadata values for the prefix
            if not cell_id:
                 search_pools = [parent_header, metadata]
                 for pool in search_pools:
                      if not isinstance(pool, dict): continue
                      for value in pool.values():
                           if isinstance(value, str) and value.startswith("vscode-notebook-cell:"):
                                cell_id = value
                                break
                      if cell_id: break

            if cell_id:
                 logger.debug(f"Detected Cell ID: ...{cell_id[-8:]}")
            else:
                 logger.debug("Could not detect Cell ID from metadata.")

        except Exception as e:
            logger.warning(f"Error detecting Cell ID: {e}", exc_info=False)
            cell_id = None # Ensure None on error

        return exec_count, cell_id

class IPythonStreamHandler(StreamCallbackHandler):
    """Handles streaming output directly to IPython display, updating a single area."""
    def __init__(self):
        self._display_id = str(uuid.uuid4())
        self._display_handle = None
        self._buffer = ""
        self._started = False
        self._final_content_displayed = False
        logger.debug(f"IPythonStreamHandler created with display_id: {self._display_id}")

    def on_stream_start(self) -> None:
        """Initializes the display area."""
        self._buffer = ""
        self._final_content_displayed = False
        try:
            # Create an initial display area with a placeholder
            self._display_handle = display(Markdown("```text\nAssistant (streaming)...\n```"), display_id=self._display_id, raw=True)
            self._started = True
            logger.debug(f"Stream display started (ID: {self._display_id}).")
        except Exception as e:
             logger.exception(f"Failed to create initial display for stream (ID: {self._display_id}).")
             self._started = False # Mark as not started if display fails

    def on_stream_chunk(self, chunk: str) -> None:
        """Updates the display area with new content."""
        if not self._started or not self._display_handle:
            logger.warning("Stream chunk received but display not started or handle lost.")
            return # Don't try to update if display setup failed

        self._buffer += chunk
        # Update the display area with accumulated content, formatted as markdown code block
        # Using raw=True to prevent potential markdown interpretation issues with partial code/text
        # Escape triple backticks within the buffer to avoid breaking the markdown block
        escaped_buffer = self._buffer.replace("```", "` ``")
        try:
            update_display(Markdown(f"```text\n{escaped_buffer}\n```"), display_id=self._display_id, raw=True)
        except Exception as e:
             # Log error but don't stop stream processing
             logger.warning(f"Failed to update display for stream chunk (ID: {self._display_id}): {e}")

    def on_stream_end(self, full_response: str) -> None:
        """Final update to the display area with the complete response."""
        if not self._started or not self._display_handle:
             # If display setup failed, print final response as fallback
             logger.warning("Stream ended but display not started. Printing final response.")
             print("\n--- Assistant Response (Stream End) ---")
             print(full_response)
             print("--------------------------------------")
             self._final_content_displayed = True
             return

        # Final update with proper markdown formatting (not just text block)
        try:
            update_display(Markdown(f"**Assistant:**\n{full_response}"), display_id=self._display_id, raw=True)
            self._final_content_displayed = True
            logger.debug(f"Stream display finished (ID: {self._display_id}).")
        except Exception as e:
             logger.exception(f"Failed to make final update to display for stream (ID: {self._display_id}). Printing fallback.")
             print("\n--- Assistant Response (Stream End - Display Error) ---")
             print(full_response)
             print("-------------------------------------------------------")
             self._final_content_displayed = True # Mark as displayed even if fallback used

        self._started = False # Reset state

    def on_stream_error(self, error: Exception) -> None:
        """Displays the error in the designated display area or prints it."""
        logger.error(f"Streaming error occurred: {error}")
        error_html = f"""
        <div style="border: 1px solid red; color: red; background-color: #ffebee; padding: 10px; margin-top: 5px; border-radius: 4px;">
        <strong>Streaming Error:</strong><br><pre style="white-space: pre-wrap; word-wrap: break-word;">{error}</pre>
        </div>
        """
        if self._started and self._display_handle and not self._final_content_displayed:
            # Update the display area to show the error
            try:
                update_display(HTML(error_html), display_id=self._display_id, raw=True)
                self._final_content_displayed = True # Error message replaces content
            except Exception as e:
                 logger.exception(f"Failed to update display with stream error (ID: {self._display_id}). Printing fallback.")
                 print(f"\nStreaming Error: {error}")
                 self._final_content_displayed = True
        elif not self._final_content_displayed:
            # Fallback to printing the error if display wasn't set up or already finalized
            print(f"\nStreaming Error: {error}")
            # Display the formatted HTML error as a fallback if possible
            try:
                 display(HTML(error_html), raw=True)
                 self._final_content_displayed = True
            except Exception:
                 pass # Ignore if display fails here too

        self._started = False # Reset state

# --- Magic Class ---

if _IPYTHON_AVAILABLE: # Only define the class if IPython is installed
    @magics_class
    class NotebookLLMMagics(Magics):
        """IPython Magics for interacting with the NotebookLLM ChatManager."""

        def __init__(self, shell):
            super().__init__(shell)
            # Attempt to initialize the manager early so setup errors are noticed sooner.
            # However, actual usage should call _get_manager() to handle errors gracefully.
            try:
                 get_chat_manager()
                 logger.info("NotebookLLMMagics initialized and ChatManager accessed successfully.")
            except Exception as e:
                 logger.error(f"Error initializing NotebookLLM during magic setup: {e}")
                 # Don't prevent magics from loading, but commands will likely fail.
                 # The error is stored in _initialization_error.

        def _get_manager(self) -> ChatManager:
            """Helper to get the manager instance, raising clearly if initialization failed."""
            try:
                # This will raise RuntimeError if _initialization_error is set
                return get_chat_manager()
            except Exception as e:
                # Provide a user-friendly error message in the notebook
                print(f"❌ NotebookLLM Error: Could not get Chat Manager.", file=sys.stderr)
                print(f"   Reason: {e}", file=sys.stderr)
                print(f"   Please check your configuration (.env file, API keys, directories) and restart the kernel.", file=sys.stderr)
                raise RuntimeError("NotebookLLM manager unavailable.") from e # Stop magic execution

        def _display_status(self, status_info: Dict[str, Any]):
            """Displays a status bar after execution using provided info."""
            duration = status_info.get("duration", 0.0)
            success = status_info.get("success", False)
            tokens_in = status_info.get("tokens_in") # Might be None
            tokens_out = status_info.get("tokens_out") # Might be None
            cost_str = status_info.get("cost_str") # Might be None
            model_used = status_info.get("model_used")

            status_parts = []
            if success:
                status_parts.append(f"✅ Success!")
            else:
                status_parts.append(f"⚠️ Failed!")

            status_parts.append(f"({duration:.2f}s)")

            if model_used:
                 status_parts.append(f"Model: {model_used}")

            token_parts = []
            if tokens_in is not None: token_parts.append(f"In: {tokens_in} tk")
            if tokens_out is not None: token_parts.append(f"Out: {tokens_out} tk")
            if token_parts: status_parts.append(", ".join(token_parts))

            if cost_str: status_parts.append(f"Est. Cost: {cost_str}")

            status_text = " | ".join(status_parts)

            if success:
                bg_color, border_color, text_color = "#e8f5e9", "#a5d6a7", "#1b5e20" # Green tones
            else:
                bg_color, border_color, text_color = "#ffebee", "#ef9a9a", "#c62828" # Red tones

            status_html = f"""
            <div style="background-color: {bg_color}; border: 1px solid {border_color}; color: {text_color};
                        padding: 5px 8px; margin-top: 8px; border-radius: 4px; font-family: sans-serif; font-size: 0.85em; line-height: 1.4;">
                {status_text}
            </div>
            """
            try:
                display(HTML(status_html))
            except Exception as e:
                 logger.warning(f"Failed to display status HTML: {e}")
                 print(f"Status: {status_text}") # Fallback to plain text

        # --- %llm_config Magic ---
        @magic_arguments()
        @argument('-p', '--persona', type=str, help="Select and activate a persona by name.")
        @argument('--show-persona', action='store_true', help="Show the currently active persona details.")
        @argument('--list-personas', action='store_true', help="List available persona names.")
        @argument('--set-override', nargs=2, metavar=('KEY', 'VALUE'), help="Set a temporary LLM param override (e.g., --set-override temperature 0.5).")
        @argument('--remove-override', type=str, metavar='KEY', help="Remove a specific override key.")
        @argument('--clear-overrides', action='store_true', help="Clear all temporary LLM param overrides.")
        @argument('--show-overrides', action='store_true', help="Show the currently active overrides.")
        @argument('--clear-history', action='store_true', help="Clear the current chat history (keeps system prompt).")
        @argument('--save', type=str, nargs='?', const=True, metavar='FILENAME', help="Save session. If no name, uses current session ID. '.md' added automatically.")
        @argument('--load', type=str, metavar='SESSION_ID', help="Load session from specified identifier (filename without .md).")
        @argument('--list-sessions', action='store_true', help="List saved session identifiers.")
        @argument('--list-snippets', action='store_true', help="List available snippet names.")
        @argument('--show-history', action='store_true', help="Display the current message history.")
        @argument('--status', action='store_true', help="Show current status (persona, overrides, history length).")
        @line_magic('llm_config')
        def configure_llm(self, line):
            """Configure the LLM session state and manage resources."""
            try:
                args = parse_argstring(self.configure_llm, line)
                manager = self._get_manager()
            except Exception as e:
                 # Error already printed by _get_manager or parse_argstring
                 return # Stop processing

            action_taken = False # Track if any action was performed

            # --- List Resources ---
            if args.list_personas:
                action_taken = True
                try:
                    personas = manager.list_personas()
                    print("Available Personas:", ", ".join(f"'{p}'" for p in personas) if personas else "None")
                except Exception as e:
                    print(f"❌ Error listing personas: {e}")

            if args.list_snippets:
                action_taken = True
                try:
                    snippets = manager.list_snippets()
                    print("Available Snippets:", ", ".join(f"'{s}'" for s in snippets) if snippets else "None")
                except Exception as e:
                    print(f"❌ Error listing snippets: {e}")

            if args.list_sessions:
                action_taken = True
                try:
                    sessions = manager.list_saved_sessions()
                    print("Saved Sessions:", ", ".join(f"'{s}'" for s in sessions) if sessions else "None")
                except Exception as e:
                    print(f"❌ Error listing saved sessions: {e}")

            # --- Manage Persona ---
            if args.persona:
                action_taken = True
                try:
                    manager.select_persona(args.persona)
                    print(f"✅ Persona activated: '{args.persona}'")
                except ResourceNotFoundError:
                    print(f"❌ Error: Persona '{args.persona}' not found.")
                except Exception as e:
                     print(f"❌ Error setting persona '{args.persona}': {e}")

            # --- Manage Overrides ---
            if args.set_override:
                action_taken = True
                key, value = args.set_override
                # Attempt basic type conversion (optional, could pass strings directly)
                try:
                     # Try float, int, then string
                     parsed_value = float(value) if '.' in value else int(value)
                except ValueError:
                     parsed_value = value # Keep as string if conversion fails
                manager.set_override(key, parsed_value)
                print(f"✅ Override set: {key} = {parsed_value} ({type(parsed_value).__name__})")

            if args.remove_override:
                 action_taken = True
                 key = args.remove_override
                 manager.remove_override(key)
                 print(f"✅ Override removed: {key}")

            if args.clear_overrides:
                action_taken = True
                manager.clear_overrides()
                print("✅ All overrides cleared.")

            # --- Manage History ---
            if args.clear_history:
                action_taken = True
                manager.clear_history()
                print("✅ Chat history cleared.")

            # --- Manage Persistence ---
            if args.load:
                action_taken = True
                try:
                    manager.load_session(args.load)
                    print(f"✅ Session loaded from '{args.load}'.")
                except ResourceNotFoundError:
                    print(f"❌ Error: Session '{args.load}' not found.")
                except PersistenceError as e:
                     print(f"❌ Error loading session '{args.load}': {e}")
                except Exception as e:
                     print(f"❌ Unexpected error loading session '{args.load}': {e}")

            # Save needs to be after load/clear etc.
            if args.save:
                action_taken = True
                try:
                    filename = args.save if isinstance(args.save, str) else None
                    save_path = manager.save_session(identifier=filename)
                    print(f"✅ Session saved to '{Path(save_path).name}'.") # Show only filename
                except PersistenceError as e:
                     print(f"❌ Error saving session: {e}")
                except Exception as e:
                     print(f"❌ Unexpected error saving session: {e}")

            # --- Show Status/Info ---
            if args.show_persona:
                 action_taken = True
                 active_persona = manager.get_active_persona()
                 if active_persona:
                      print(f"Active Persona: '{active_persona.name}'")
                      print(f"  System Prompt: {active_persona.system_prompt[:100]}{'...' if len(active_persona.system_prompt)>100 else ''}")
                      print(f"  LLM Params: {active_persona.llm_params}")
                 else:
                      print("Active Persona: None")

            if args.show_overrides:
                 action_taken = True
                 overrides = manager.get_overrides()
                 print("Active Overrides:", overrides if overrides else "None")

            if args.show_history:
                 action_taken = True
                 history = manager.get_history()
                 print(f"--- History ({len(history)} messages) ---")
                 if not history:
                      print("(empty)")
                 else:
                      for i, msg in enumerate(history):
                           print(f"[{i}] {msg.role.upper()}: {msg.content[:150]}{'...' if len(msg.content)>150 else ''}")
                           print(f"    (ID: ...{msg.id[-6:]}, Cell: {msg.cell_id[-8:] if msg.cell_id else 'N/A'}, Exec: {msg.execution_count})")
                 print("--------------------------")

            # Default action or if explicitly requested: show status
            if args.status or not action_taken:
                 active_persona = manager.get_active_persona()
                 overrides = manager.get_overrides()
                 history = manager.get_history()
                 print("--- NotebookLLM Status ---")
                 print(f"Session ID: {manager._session_id}") # Access internal for status
                 print(f"Active Persona: '{active_persona.name}'" if active_persona else "None")
                 print(f"Active Overrides: {overrides if overrides else 'None'}")
                 print(f"History Length: {len(history)} messages")
                 print("--------------------------")

        # --- %%llm Cell Magic ---
        @magic_arguments()
        # Runtime arguments overriding session state for this call only
        @argument('-p', '--persona', type=str, help="Use specific persona for THIS call only.")
        @argument('-m', '--model', type=str, help="Use specific model for THIS call only.")
        @argument('-t', '--temperature', type=float, help="Set temperature for THIS call.")
        @argument('--max-tokens', type=int, dest='max_tokens', help="Set max_tokens for THIS call.")
        # Behavior control arguments
        @argument('--no-history', action='store_false', dest='add_to_history', help="Do not add this exchange to history.")
        @argument('--no-stream', action='store_false', dest='stream', help="Do not stream output (wait for full response).")
        @argument('--no-rollback', action='store_false', dest='auto_rollback', help="Disable auto-rollback check for this cell run.")
        # Snippet arguments
        @argument('--snippet', type=str, action='append', help="Add user snippet content before sending prompt. Can be used multiple times.")
        @argument('--sys-snippet', type=str, action='append', help="Add system snippet content before sending prompt. Can be used multiple times.")
        # Add other common LLM params as needed (e.g., top_p, frequency_penalty)
        @argument('--param', nargs=2, metavar=('KEY', 'VALUE'), action='append', help="Set any other LLM param ad-hoc (e.g., --param top_p 0.9).")
        @cell_magic('llm')
        async def execute_llm(self, line, cell):
            """Send the cell content as a prompt to the LLM, applying arguments."""
            start_time = time.time()
            status_info = {"success": False, "duration": 0.0} # Initialize status dict

            try:
                args = parse_argstring(self.execute_llm, line)
                manager = self._get_manager()
            except Exception as e:
                 status_info["duration"] = time.time() - start_time
                 self._display_status(status_info)
                 return # Stop processing

            prompt = cell.strip()
            if not prompt:
                print("⚠️ LLM prompt is empty, skipping.")
                status_info["duration"] = time.time() - start_time
                self._display_status(status_info)
                return

            # Handle snippets first - add them to history before the user prompt
            try:
                if args.sys_snippet:
                    for name in args.sys_snippet:
                        if not manager.add_snippet(name, role='system'):
                            print(f"⚠️ Warning: Could not add system snippet '{name}'.")
                if args.snippet:
                    for name in args.snippet:
                         if not manager.add_snippet(name, role='user'):
                              print(f"⚠️ Warning: Could not add user snippet '{name}'.")
            except SnippetError as e:
                 print(f"❌ Error adding snippet: {e}")
                 status_info["duration"] = time.time() - start_time
                 self._display_status(status_info)
                 return # Stop if snippet addition fails critically
            except Exception as e:
                 print(f"❌ Unexpected error processing snippets: {e}")
                 status_info["duration"] = time.time() - start_time
                 self._display_status(status_info)
                 return

            # Prepare runtime params and stream handler
            runtime_params = {}
            if args.model: runtime_params['model'] = args.model
            if args.temperature is not None: runtime_params['temperature'] = args.temperature
            if args.max_tokens is not None: runtime_params['max_tokens'] = args.max_tokens
            if args.param:
                 for key, value in args.param:
                      # Attempt type conversion for ad-hoc params
                      try:
                           parsed_value = float(value) if '.' in value else int(value)
                      except ValueError:
                           parsed_value = value # Keep as string
                      runtime_params[key] = parsed_value

            stream_handler = IPythonStreamHandler() if args.stream else None
            assistant_message: Optional[Message] = None

            try:
                assistant_message = await manager.send_message(
                    prompt=prompt,
                    persona_name=args.persona, # Temporary persona if specified
                    stream_handler=stream_handler,
                    add_to_history=args.add_to_history,
                    auto_rollback=args.auto_rollback,
                    **runtime_params
                )
                status_info["success"] = True

                # --- TODO: Extract token counts and cost ---
                # This requires ChatManager to store/return this info from the LLM response
                # Placeholder values:
                tokens_in = assistant_message.metadata.get("token_usage", {}).get("prompt_tokens") if assistant_message else None
                tokens_out = assistant_message.metadata.get("token_usage", {}).get("completion_tokens") if assistant_message else None
                status_info["tokens_in"] = tokens_in
                status_info["tokens_out"] = tokens_out
                status_info["model_used"] = assistant_message.metadata.get("model_used") if assistant_message else runtime_params.get('model') or manager.get_active_persona().llm_params.get('model') # Best guess
                # Cost calculation needs model costs (complex) - Placeholder
                if tokens_in is not None and tokens_out is not None:
                     cost_milli_cents = tokens_in * 0.005 + tokens_out * 0.015 # Example rates
                     status_info["cost_str"] = f"~${cost_milli_cents / 1000:.4f}"

            except NotebookLLMError as e:
                print(f"❌ LLM Error: {e}") # Display user-friendly errors
            except Exception as e:
                print(f"❌ An unexpected error occurred: {e}")
                logger.exception("Unexpected error during %%llm execution.") # Log traceback
            finally:
                status_info["duration"] = time.time() - start_time
                self._display_status(status_info) # Display status bar

            # If not streaming and successful, display the result cleanly
            if not stream_handler and assistant_message and status_info["success"]:
                display(Markdown(f"**Assistant:**\n{assistant_message.content}"))

        # --- TODO: Implement Auto-Magic Transformer ---
        # This requires defining _auto_magic_transformer and registering/unregistering it
        # with ip.input_transformers_cleanup. It's more complex. Need `llm_setup_forever` etc.

else:
    # If IPython is not available, define a placeholder class
    class NotebookLLMMagics:
        def __init__(self, shell=None):
            logger.warning("IPython not found. NotebookLLM magics are disabled.")
        # Add dummy methods if needed to prevent attribute errors elsewhere
        def configure_llm(self, line): pass
        async def execute_llm(self, line, cell): pass

# --- Extension Loading ---

def load_ipython_extension(ipython):
    """Registers the magics with the IPython runtime."""
    if not _IPYTHON_AVAILABLE:
        print("IPython is not available. Cannot load NotebookLLM magics.", file=sys.stderr)
        return
    try:
        ipython.register_magics(NotebookLLMMagics)
        print("✅ NotebookLLM Magics loaded. Use %llm_config and %%llm.")
        # Optionally display initial status
        # get_chat_manager().status() # Needs a status method or call configure_llm("")
    except Exception as e:
         logger.exception("Failed to register NotebookLLM magics.")
         print(f"❌ Failed to load NotebookLLM Magics: {e}", file=sys.stderr)

def unload_ipython_extension(ipython):
    """Unregisters the magics (optional but good practice)."""
    if not _IPYTHON_AVAILABLE:
        return
    # Magics are typically not explicitly unloaded, but possible if needed.
    # Check if NotebookLLMMagics is registered before trying to unregister
    # if NotebookLLMMagics in ipython.magics_manager.registry:
    #     ipython.magics_manager.unregister(NotebookLLMMagics)
    #     print("NotebookLLM Magics unloaded.")
    # For simplicity, often omitted. Kernel restart achieves the same.
    logger.info("NotebookLLM extension unload requested (typically no action needed).")

EOF

# --- Populate utils/logging.py ---
echo "Populating ${SRC_BASE}/utils/logging.py..."
cat << 'EOF' > "${SRC_BASE}/utils/logging.py"
import logging
import sys
from ..config import settings # Import settings to get log level

_initialized = False

def setup_logging():
    """Configures logging for the application based on settings."""
    global _initialized
    if _initialized:
        return

    log_level_str = settings.log_level.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Basic configuration - modify formatter and handlers as needed
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configure root logger or specific package logger
    # Configuring root logger can affect other libraries, be careful
    # logger = logging.getLogger("notebook_llm") # Get package-specific logger
    logger = logging.getLogger() # Get root logger
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates if called multiple times (though _initialized prevents this)
    # for handler in logger.handlers[:]:
    #     logger.removeHandler(handler)

    # Add a handler (e.g., StreamHandler to stderr/stdout)
    # Avoid adding handlers if they already exist from a parent logger setup
    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stderr) # Log to stderr by default
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.info(f"Root logger configured with level {log_level_str}.")
    else:
         logger.info(f"Logger already has handlers. Ensuring level is {log_level_str}.")

    # Propagate settings to libraries like LiteLLM if desired
    try:
         import litellm
         # LiteLLM verbose maps roughly to DEBUG
         litellm.set_verbose = (log_level <= logging.DEBUG)
         logger.debug(f"Set litellm.set_verbose to {litellm.set_verbose}")
    except ImportError:
         pass # LiteLLM not installed
    except Exception as e:
         logger.warning(f"Could not configure LiteLLM logging: {e}")

    _initialized = True

def get_logger(name: str) -> logging.Logger:
    """Gets a logger instance, ensuring setup_logging has been called."""
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)

# Call setup automatically when the module is imported?
# Or rely on explicit call from __init__.py or application entry point.
# Calling it here ensures logging is set up whenever get_logger is first called.
# setup_logging() # Optional: uncomment to auto-setup on import

EOF

# --- Populate __init__.py files ---
echo "Populating __init__.py files..."
# Main __init__
cat << 'EOF' > "${SRC_BASE}/__init__.py"
__version__ = '0.1.0'

# Configure logging as early as possible
from .utils.logging import setup_logging
setup_logging()

# Expose key classes and exceptions for easier import by users
from .chat_manager import ChatManager
from .exceptions import (
    NotebookLLMError,
    ConfigurationError,
    ResourceNotFoundError,
    LLMInteractionError,
    HistoryManagementError,
    PersistenceError,
    SnippetError
)
# Expose interfaces if they are intended for external implementation/type hinting
from .interfaces import (
    LLMClientInterface,
    PersonaLoader,
    SnippetProvider,
    HistoryStore,
    ContextProvider,
    StreamCallbackHandler
)
# Expose core models
from .models import Message, PersonaConfig, ConversationMetadata

# --- Optional: Provide a default factory function ---
# This simplifies setup for basic use cases

_default_manager_instance = None

def get_default_manager():
    """
    Gets or creates a default ChatManager instance with standard file-based components.
    Requires IPython for default context provider.
    """
    global _default_manager_instance
    if _default_manager_instance is None:
        try:
            # Import components needed for the default setup
            from .config import settings
            from .adapters.llm_client import LiteLLMAdapter
            from .resources.file_loader import FileLoader
            from .storage.markdown_store import MarkdownStore
            try:
                 from .integrations.ipython_magic import IPythonContextProvider
                 context_provider = IPythonContextProvider()
            except ImportError:
                 # IPython not available, use None for context
                 context_provider = None

            loader = FileLoader(settings.personas_dir, settings.snippets_dir)
            store = MarkdownStore(settings.save_dir)
            client = LiteLLMAdapter()

            _default_manager_instance = ChatManager(
                settings=settings,
                llm_client=client,
                persona_loader=loader,
                snippet_provider=loader,
                history_store=store,
                context_provider=context_provider
            )
        except Exception as e:
             # Log or raise a more specific setup error
             raise NotebookLLMError(f"Failed to create default ChatManager: {e}") from e
    return _default_manager_instance

__all__ = [
    "ChatManager",
    "get_default_manager",
    # Exceptions
    "NotebookLLMError",
    "ConfigurationError",
    "ResourceNotFoundError",
    "LLMInteractionError",
    "HistoryManagementError",
    "PersistenceError",
    "SnippetError",
    # Interfaces
    "LLMClientInterface",
    "PersonaLoader",
    "SnippetProvider",
    "HistoryStore",
    "ContextProvider",
    "StreamCallbackHandler",
    # Models
    "Message",
    "PersonaConfig",
    "ConversationMetadata",
    # Version
    "__version__",
]
EOF

# Subdirectory __init__ files (can often remain empty unless exposing specific things)
touch "${SRC_BASE}/resources/__init__.py"
touch "${SRC_BASE}/storage/__init__.py"
touch "${SRC_BASE}/adapters/__init__.py"
touch "${SRC_BASE}/integrations/__init__.py"
touch "${SRC_BASE}/utils/__init__.py"

echo "✅ Python files populated successfully!"
echo "➡️ Next steps:"
echo "   1. Implement the logic within the methods (marked with # --- TODO --- or containing '...')."
echo "   2. Write unit and integration tests for your implementations."
echo "   3. Refine models, interfaces, and error handling as needed during development."

exit 0