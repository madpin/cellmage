import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Union

from langchain_core.callbacks import StreamingStdOutCallbackHandler

# Import from langchain-openai package for LangChain 0.3.24
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..exceptions import ConfigurationError, LLMInteractionError
from ..interfaces import LLMClientInterface, StreamCallbackHandler
from ..models import Message


class LangChainStreamingCallbackHandler(StreamingStdOutCallbackHandler):
    """Custom callback handler to capture streaming output from LangChain."""

    def __init__(self, callback: Optional[StreamCallbackHandler]):
        super().__init__()
        self.callback = callback
        self.captured_text = ""

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Process a new token in the stream."""
        self.captured_text += token
        if self.callback:
            self.callback(token)


class LangChainAdapter(LLMClientInterface):
    """
    Adapter for LLM interactions using LangChain.

    This adapter provides access to language models through the LangChain library,
    offering more advanced conversational capabilities and integrations.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        default_model: Optional[str] = None,
        debug: bool = False,
    ):
        """
        Initialize the LangChain adapter.

        Args:
            api_key: API key for the service
            api_base: Base URL for the API
            default_model: Default model to use
            debug: Whether to enable debug logging
        """
        self.logger = logging.getLogger(__name__)

        # Instance overrides (similar to DirectLLMAdapter)
        self._instance_overrides: Dict[str, Any] = {}
        self._last_model_used = None

        # Set API key from param or env var
        api_key = api_key or os.environ.get("CELLMAGE_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if api_key:
            self.set_override("api_key", api_key)

        # Set API base from param or env var
        api_base = (
            api_base or os.environ.get("CELLMAGE_API_BASE") or os.environ.get("OPENAI_API_BASE")
        )
        if api_base:
            self.set_override("api_base", api_base)

        # Set default model if provided
        if default_model:
            self.set_override("model", default_model)

        # Set debug mode
        self.debug = debug

    def set_override(self, key: str, value: Any) -> None:
        """Set an instance-level override for parameters."""
        # Mask secrets in logs
        if key in ["api_key", "aws_secret_access_key"] and isinstance(value, str):
            value_repr = value if len(value) <= 16 else value[:4] + "..." + value[-4:]
            self.logger.info(f"[Override] Setting '{key}' = {value_repr}")
        else:
            self.logger.info(f"[Override] Setting '{key}' = {value}")
        self._instance_overrides[key] = value

    def remove_override(self, key: str) -> None:
        """Remove an instance-level override."""
        if key in self._instance_overrides:
            self.logger.info(f"[Override] Removed '{key}'")
            del self._instance_overrides[key]
        else:
            self.logger.debug(f"[Override] Key '{key}' not found, nothing removed.")

    def clear_overrides(self) -> None:
        """
        Remove all instance-level overrides except api_key and api_base.
        For model, reset it to the default from settings.
        """
        # Save api_key, api_base and default model
        api_key = self._instance_overrides.get("api_key")
        api_base = self._instance_overrides.get("api_base")

        # Import settings to get the default model
        from ..config import settings

        default_model = settings.default_model

        # Clear all overrides
        self._instance_overrides = {}

        # Restore the preserved values
        if api_key is not None:
            self._instance_overrides["api_key"] = api_key

        if api_base is not None:
            self._instance_overrides["api_base"] = api_base

        # Set model to the default value
        if default_model is not None:
            self._instance_overrides["model"] = default_model

        self.logger.info(
            "[Override] Overrides cleared, preserving api_key and api_base. Model reset to default."
        )

    def get_overrides(self) -> Dict[str, Any]:
        """
        Get the current LLM parameter overrides.

        Returns:
            A dictionary of current override parameters
        """
        return self._instance_overrides.copy()

    def _convert_to_langchain_messages(self, messages: List[Message]) -> List[BaseMessage]:
        """
        Convert our Message objects to LangChain message objects, supporting multimodal (text + image) messages.
        If a message's metadata contains 'llm_image', the content will be a list with text and image_url dicts.
        """
        langchain_messages = []
        for msg in messages:
            llm_image = msg.metadata.get("llm_image") if hasattr(msg, "metadata") else None
            if msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                if llm_image:
                    content_list = []
                    if msg.content and msg.content.strip():
                        content_list.append({"type": "text", "text": msg.content})
                    content_list.append(llm_image)
                    langchain_messages.append(HumanMessage(content=content_list))
                else:
                    langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role in ["assistant", "ai"]:
                langchain_messages.append(AIMessage(content=msg.content))
            else:
                langchain_messages.append(HumanMessage(content=f"[{msg.role}]: {msg.content}"))
        return langchain_messages

    def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        stream: bool = False,
        stream_callback: Optional[StreamCallbackHandler] = None,
        **kwargs,
    ) -> Union[str, None]:
        """
        Send messages to the LLM using LangChain and get a response.

        Args:
            messages: List of Message objects to send
            model: Override model to use for this request
            stream: Whether to stream the response
            stream_callback: Callback to handle streaming responses
            **kwargs: Additional parameters for the LLM

        Returns:
            The model's response as a string or None if there was an error
        """
        try:
            # Extract message_id and conversation_id if available
            message_id = None
            conversation_id = None

            # Try to get message ID from the last message in the conversation
            if messages and len(messages) > 0:
                last_message = messages[-1]
                if hasattr(last_message, "id") and last_message.id:
                    message_id = last_message.id

                # Try to get conversation ID from message metadata
                if hasattr(last_message, "metadata") and last_message.metadata:
                    if "conversation_id" in last_message.metadata:
                        conversation_id = last_message.metadata["conversation_id"]

            # Also check in kwargs for conversation_id
            if "conversation_id" in kwargs:
                conversation_id = kwargs.pop("conversation_id")

            # Record start time for response time tracking
            import datetime

            start_time = datetime.datetime.now()

            # Get API credentials and model
            api_key = kwargs.pop("api_key", None) or self._instance_overrides.get("api_key")
            api_base = kwargs.pop("api_base", None) or self._instance_overrides.get("api_base")
            final_model = (
                model or kwargs.pop("model", None) or self._instance_overrides.get("model")
            )

            if not api_key:
                raise ConfigurationError(
                    "No API key specified. Provide via api_key parameter in constructor, "
                    "set_override('api_key'), or set CELLMAGE_API_KEY environment variable."
                )

            if not final_model:
                raise ConfigurationError(
                    "No model specified. Provide via model parameter, set_override('model'), or in the constructor."
                )

            # Configure LangChain streaming handler if needed
            streaming_handler = None
            if stream:
                streaming_handler = LangChainStreamingCallbackHandler(stream_callback)

            # Get headers from settings
            from ..config import settings

            # Create LangChain ChatOpenAI instance with appropriate configs
            chat_params = {
                "model": final_model,
                "api_key": api_key,
                "streaming": stream,
                "temperature": kwargs.pop("temperature", 0.7),
                "model_kwargs": {"extra_headers": settings.request_headers},
            }

            # Set API base URL if provided - must be done during initialization
            if api_base:
                chat_params["base_url"] = api_base

            if streaming_handler:
                chat_params["callbacks"] = [streaming_handler]

            # Add any remaining kwargs
            chat_params.update(kwargs)

            # Create a copy of the parameters for raw response storage
            request_data = {
                "model": final_model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": stream,
                "temperature": chat_params.get("temperature", 0.7),
                # Don't include API key in stored data
            }

            # Create the ChatOpenAI instance with all params
            chat = ChatOpenAI(**chat_params)

            # Convert our messages to LangChain format
            lc_messages = self._convert_to_langchain_messages(messages)

            # Generate response
            if stream:
                # For streaming, we invoke the model and let the callback handle tokens
                response = chat.invoke(lc_messages)
                # The streaming handler already called the callbacks
                # Just return the collected response
                result = "" if not streaming_handler else streaming_handler.captured_text
            else:
                # For non-streaming, get the content directly
                response = chat.invoke(lc_messages)
                # In 0.3.24, response is an AIMessage object with a content attribute
                if not response:
                    return ""
                # Ensure result is properly typed as a string
                if hasattr(response, "content"):
                    result = str(response.content)
                else:
                    result = ""

            # Calculate response time in milliseconds
            response_time_ms = int((datetime.datetime.now() - start_time).total_seconds() * 1000)

            # Create a reconstructed response object for storage
            response_data = {
                "id": str(uuid.uuid4()),
                "object": "chat.completion",
                "created": int(datetime.datetime.now().timestamp()),
                "model": final_model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": result},
                        "finish_reason": "stop",
                    }
                ],
                # LangChain doesn't provide token usage information directly
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "_langchain_reconstructed": True,
            }

            # Create endpoint URL
            endpoint = f"{api_base}/chat/completions" if api_base else "langchain_adapter"

            # Store raw API response
            self._store_raw_api_response(
                request_data=request_data,
                response_data=response_data,
                endpoint=endpoint,
                response_time_ms=response_time_ms,
                message_id=message_id,
                conversation_id=conversation_id,
            )

            # Store the model used for status reporting
            self._last_model_used = final_model
            self._instance_overrides["model"] = final_model

            return result.strip()

        except Exception as e:
            self.logger.error(f"Error in LangChain chat request: {e}")
            if self.debug:
                self.logger.exception("Exception details")
            raise LLMInteractionError(f"LangChain chat request failed: {e}") from e

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Fetch available models from the configured endpoint.

        Returns:
            List of model dictionaries or empty list if failed
        """
        # Extract api_base and api_key from instance overrides
        api_base = self._instance_overrides.get("api_base")
        api_key = self._instance_overrides.get("api_key")

        if not api_base or not api_key:
            self.logger.error("Cannot fetch models: Missing API base URL or API key")
            return []

        try:
            # Create a temporary ChatOpenAI instance to access models
            # Note: LangChain 0.3.24 doesn't provide a direct way to list models
            chat_params = {"api_key": api_key}

            if api_base:
                chat_params["base_url"] = api_base

            _ = ChatOpenAI(**chat_params)

            # This is a simplified implementation as LangChain doesn't provide
            # a direct way to list models. We'd need to make a custom request.
            # For now, we return a simplified list of common models
            return [
                {"id": "gpt-4.1-nano", "name": "GPT-3.5 Turbo"},
                {"id": "gpt-4o", "name": "GPT-4o"},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            ]

        except Exception as e:
            self.logger.error(f"Error fetching models: {e}")
            return []

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific model.

        Args:
            model_name: The name of the model to query

        Returns:
            Dictionary with model information or None on error
        """
        # LangChain doesn't provide a direct way to get model info
        # This is a simplified implementation

        # Updated with latest model information as of April 2025
        model_info = {
            "gpt-4.1-nano": {
                "id": "gpt-4.1-nano",
                "name": "GPT-3.5 Turbo",
                "description": "Most capable GPT-3.5 model and optimized for chat",
                "context_window": 16385,
            },
            "gpt-4o": {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "description": "Latest GPT-4 model with improved capabilities and vision",
                "context_window": 128000,
            },
            "gpt-4o-mini": {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "description": "Smaller, more efficient version of GPT-4o",
                "context_window": 128000,
            },
        }

        return model_info.get(model_name)

    def get_last_model_used(self) -> Optional[str]:
        """
        Get the model that was used in the last API call.

        Returns:
            Model name or None if no call has been made
        """
        return self._last_model_used

    def _get_sqlite_store(self) -> Optional[Any]:
        """
        Get the SQLiteStore instance if SQLite storage is configured.

        Returns:
            SQLiteStore instance or None if not configured
        """
        try:
            from ..config import settings

            if settings.storage_type == "sqlite":
                from ..storage.sqlite_store import SQLiteStore

                return SQLiteStore()
            return None
        except ImportError:
            self.logger.warning("SQLite storage not available")
            return None

    def _store_raw_api_response(
        self,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        endpoint: str,
        response_time_ms: int,
        message_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> None:
        """
        Store raw API request and response data to SQLite if configured.

        Args:
            request_data: The request payload sent to the API
            response_data: The response data received from the API
            endpoint: The API endpoint URL
            response_time_ms: The response time in milliseconds
            message_id: Optional ID of the message this response is associated with
            conversation_id: Optional ID of the conversation this response is associated with
        """
        # Check if storing raw responses is enabled in settings
        from ..config import settings

        if not getattr(settings, "store_raw_responses", False):
            # Skip storing raw responses if not enabled
            self.logger.debug("Skipping raw API response storage (disabled in settings)")
            return

        sqlite_store = self._get_sqlite_store()
        if sqlite_store:
            try:
                # Create default message and conversation IDs if not provided
                if message_id is None:
                    message_id = str(uuid.uuid4())

                if conversation_id is None:
                    conversation_id = str(uuid.uuid4())

                status_code = 200  # Assuming success since we got here

                sqlite_store.store_raw_api_response(
                    message_id=message_id,
                    conversation_id=conversation_id,
                    endpoint=endpoint,
                    request_data=request_data,
                    response_data=response_data,
                    response_time_ms=response_time_ms,
                    status_code=status_code,
                )

                self.logger.debug(f"Stored raw API response for message {message_id}")
            except Exception as e:
                # Don't let errors in storing raw responses affect the main flow
                self.logger.warning(f"Failed to store raw API response: {e}")
                if self.debug:
                    self.logger.exception("Exception details")
