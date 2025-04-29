import json
import logging
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    import requests
else:
    import requests  # type: ignore

from ..exceptions import ConfigurationError, LLMInteractionError
from ..interfaces import LLMClientInterface, StreamCallbackHandler
from ..models import Message


class DirectLLMAdapter(LLMClientInterface):
    """
    Adapter for direct HTTP interaction with OpenAI-compatible APIs.

    This adapter handles communication with OpenAI and compatible APIs
    without requiring external libraries like litellm.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        default_model: Optional[str] = None,
        debug: bool = False,
    ):
        """
        Initialize the adapter.

        Args:
            api_key: API key for the service
            api_base: Base URL for the API
            default_model: Default model to use
            debug: Whether to enable debug logging
        """
        self.logger = logging.getLogger(__name__)

        # Instance overrides
        self._instance_overrides: Dict[str, Any] = {}
        # Track the last token usage
        self._last_token_usage: Dict[str, int] = {}
        # Track the last model used
        self._last_model_used: Optional[str] = None

        # Initialize model mapper and try to load default mappings
        from ..model_mapping import ModelMapper

        self.model_mapper = ModelMapper()

        # Try to find and load default mapping file
        mapping_file = ModelMapper.find_mapping_file()
        if mapping_file:
            self.model_mapper.load_mappings(mapping_file)
            self.logger.info(f"Loaded model mappings from {mapping_file}")

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

    def _ensure_model_has_provider(self, model_name: Optional[str]) -> Optional[str]:
        """
        Ensure the model name is properly formatted.
        Unlike litellm, we don't need to add provider prefixes for this adapter.

        Args:
            model_name: The model name to check

        Returns:
            The model name, possibly modified, or None if input is None
        """
        if not model_name:
            return None

        # For this adapter, we maintain the original model name
        return model_name

    def _determine_model_and_config(
        self,
        model_name: Optional[str],
        system_message: Optional[str],
        call_overrides: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Determine the model and configuration to use.

        Args:
            model_name: Model name to use
            system_message: System message if any
            call_overrides: Call-specific overrides

        Returns:
            Tuple of (model_name, config_dict)
        """
        # Start with the default config (empty dict)
        final_config = {}

        # Layer in instance overrides
        final_config.update(self._instance_overrides)

        # Layer in call overrides
        final_config.update(call_overrides)

        # Get model name with priority:
        # 1. Call overrides
        # 2. Instance overrides
        # 3. Model name passed to this method
        model_alias = (
            call_overrides.get("model") or self._instance_overrides.get("model") or model_name
        )

        # Translate model alias to full name
        final_model = self.model_mapper.get_full_name(model_alias) if model_alias else None

        # Store original model alias for reference
        if model_alias and model_alias != final_model:
            self.logger.info(f"Translated model alias '{model_alias}' to '{final_model}'")

        if not final_model:
            raise ConfigurationError(
                "No model specified. Provide via model parameter, set_override('model'), or in the constructor."
            )

        # Remove model from config since it's passed separately
        final_config.pop("model", None)

        # Filter out non-API fields that could cause issues
        # Common fields in persona config that shouldn't be sent to API
        fields_to_remove = ["name", "description", "original_name", "source_path"]
        for field in fields_to_remove:
            if field in final_config:
                self.logger.debug(f"Removing non-API field from config: {field}")
                final_config.pop(field, None)

        return final_model, final_config

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
            The model's response as a string or None if there was an error
        """
        try:
            # Prepare system message and other messages
            system_message = next((m.content for m in messages if m.role == "system"), None)

            # Determine model and config for this call
            final_model, final_config = self._determine_model_and_config(
                model, system_message, kwargs
            )

            # Get API credentials
            api_key = final_config.pop("api_key", None)
            api_base = final_config.pop("api_base", None)

            if not api_base:
                raise ConfigurationError(
                    "No API base URL specified. Provide via api_base parameter in constructor, "
                    "set_override('api_base'), or set CELLMAGE_API_BASE environment variable."
                )

            if not api_key:
                raise ConfigurationError(
                    "No API key specified. Provide via api_key parameter in constructor, "
                    "set_override('api_key'), or set CELLMAGE_API_KEY environment variable."
                )

            # Get headers from settings
            from ..config import settings

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                **settings.request_headers,
            }

            # Convert messages to the format expected by the API
            api_messages = []
            for msg in messages:
                api_messages.append({"role": msg.role, "content": msg.content})

            # Prepare request payload
            payload = {"model": final_model, "messages": api_messages, "stream": stream}

            # Add any remaining parameters from final_config
            payload.update(final_config)

            # Make the API call
            if stream:
                return self._handle_streaming(api_base, headers, payload, stream_callback)
            else:
                response_content = self._handle_non_streaming(api_base, headers, payload)

                # Store the actual model used from the API response in our instance overrides
                # This allows retrieving the model in status reporting
                self._last_model_used = final_model

                return response_content

        except Exception as e:
            self.logger.error(f"Error in chat request: {e}")
            if self.debug:
                self.logger.exception("Exception details")
            raise LLMInteractionError(f"Chat request failed: {e}") from e

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert our Message objects to the format expected by the API."""
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def _handle_non_streaming(
        self, api_base: str, headers: Dict[str, str], payload: Dict[str, Any]
    ) -> str:
        """Handle non-streaming API response."""
        url = f"{api_base}/chat/completions"

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60,  # Default timeout of 60 seconds
        )

        # Check for errors
        if response.status_code != 200:
            self._handle_error_response(response)

        # Parse the response
        result = response.json()

        # Extract token usage information
        self._extract_token_usage(result)

        # Store the actual model used from the response
        if "model" in result:
            self._last_model_used = result["model"]
            # Update model in instance overrides to make it available for status reporting
            self._instance_overrides["model"] = result["model"]

        # Extract the assistant's message
        if "choices" in result and len(result["choices"]) > 0:
            if "message" in result["choices"][0]:
                content = result["choices"][0]["message"].get("content", "")
                return content.strip()

        return ""

    def _extract_token_usage(self, response_data: Dict[str, Any]) -> None:
        """Extract token usage information from API response."""
        if "usage" in response_data:
            usage = response_data["usage"]
            self._last_token_usage = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
            self.logger.debug(
                f"Token usage: {self._last_token_usage['prompt_tokens']} (prompt) + "
                f"{self._last_token_usage['completion_tokens']} (completion) = "
                f"{self._last_token_usage['total_tokens']} (total)"
            )
        else:
            self._last_token_usage = {}
            self.logger.debug("No token usage information in API response")

    def get_last_token_usage(self) -> Dict[str, int]:
        """
        Get token usage from the last API call.

        Returns:
            Dictionary with prompt_tokens, completion_tokens, and total_tokens
        """
        return self._last_token_usage.copy()

    def get_last_model_used(self) -> Optional[str]:
        """
        Get the model that was used in the last API call.

        Returns:
            Model name or None if no call has been made
        """
        return self._last_model_used

    def _handle_streaming(
        self,
        api_base: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        stream_callback: Optional[StreamCallbackHandler],
    ) -> str:
        """Handle streaming API response."""
        url = f"{api_base}/chat/completions"

        # Use a session for streaming
        session = requests.Session()

        # Set stream=True for requests to get response in chunks
        response = session.post(
            url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=60,  # Default timeout of 60 seconds
        )

        # Check for errors
        if response.status_code != 200:
            self._handle_error_response(response)

        accumulated_content = ""
        model_from_stream = None
        # For streaming responses, we need to look for token usage in the final chunk
        token_usage_data = {}

        # Process the streaming response
        for line in response.iter_lines():
            if not line:
                continue

            # Remove 'data: ' prefix
            if line.startswith(b"data: "):
                line = line[6:]

            # Skip "[DONE]" message
            if line == b"[DONE]":
                break

            try:
                # Parse the JSON chunk
                chunk_data = json.loads(line)

                # Get the model from the first chunk
                if model_from_stream is None and "model" in chunk_data:
                    model_from_stream = chunk_data["model"]
                    # Update model in instance overrides to make it available for status reporting
                    self._instance_overrides["model"] = model_from_stream

                # Check if this chunk has token usage data (typically in the final chunk)
                if "usage" in chunk_data:
                    token_usage_data = chunk_data["usage"]

                # Extract content from choices
                if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                    choice = chunk_data["choices"][0]
                    if "delta" in choice and "content" in choice["delta"]:
                        content = choice["delta"]["content"]
                        if content:
                            accumulated_content += content
                            if stream_callback:
                                stream_callback(content)
            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse streaming JSON: {line}")
                continue

        # Store the actual model used from the streaming response
        if model_from_stream:
            self._last_model_used = model_from_stream

        # Update token usage from streaming response (if available)
        if token_usage_data:
            self._last_token_usage = {
                "prompt_tokens": token_usage_data.get("prompt_tokens", 0),
                "completion_tokens": token_usage_data.get("completion_tokens", 0),
                "total_tokens": token_usage_data.get("total_tokens", 0),
            }
        else:
            # If we didn't get token usage data in the stream, make an estimate based on char count
            # This is a very rough approximation and should be improved
            self._last_token_usage = {
                "prompt_tokens": 0,  # Can't accurately determine this from streaming
                "completion_tokens": len(accumulated_content)
                // 4,  # Rough estimate: 4 chars per token
                "total_tokens": 0,  # Can't accurately determine this from streaming
            }

        return accumulated_content

    def _handle_error_response(self, response: requests.Response) -> None:
        """Handle error responses from the API."""
        try:
            error_info = response.json()
            error_message = error_info.get("error", {}).get("message", "Unknown error")
            _ = error_info.get("error", {}).get("type", "Unknown error type")
            status_code = response.status_code

            if status_code == 401:
                raise LLMInteractionError(f"Authentication failed: {error_message}")
            elif status_code == 403:
                raise LLMInteractionError(f"Authorization failed: {error_message}")
            elif status_code == 404:
                raise LLMInteractionError(f"Resource not found: {error_message}")
            elif status_code == 429:
                raise LLMInteractionError(f"Rate limit exceeded: {error_message}")
            elif status_code >= 500:
                raise LLMInteractionError(f"Server error: {error_message}")
            else:
                raise LLMInteractionError(f"API error ({status_code}): {error_message}")
        except json.JSONDecodeError:
            # If the response isn't valid JSON, return the raw text or status
            error_text = response.text[:100] if response.text else f"HTTP {response.status_code}"
            raise LLMInteractionError(f"API error: {error_text}")

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Fetch available models from the configured endpoint.

        Returns:
            List of model dictionaries or empty list if failed
        """
        # Extract api_base and api_key from instance overrides
        api_base = self._instance_overrides.get("api_base")
        api_key = self._instance_overrides.get("api_key")

        if not api_base:
            self.logger.error("Cannot fetch models: No API base URL configured")
            return []

        # Ensure api_base ends with /v1 for OpenAI compatibility
        if not api_base.endswith("/v1"):
            api_base = f"{api_base}/v1" if not api_base.endswith("/") else f"{api_base}v1"

        models_url = f"{api_base}/models"

        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = requests.get(models_url, headers=headers, timeout=10)
            response.raise_for_status()

            models_data = response.json()
            if "data" in models_data and isinstance(models_data["data"], list):
                self.logger.info(f"Successfully fetched {len(models_data['data'])} models")
                return models_data["data"]
            else:
                self.logger.warning("Unexpected response format from models endpoint")
                return []
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
        # Extract api_base and api_key from instance overrides
        api_base = self._instance_overrides.get("api_base")
        api_key = self._instance_overrides.get("api_key")

        if not api_base:
            self.logger.error("Cannot fetch model info: No API base URL configured")
            return None

        # Ensure api_base ends with /v1 for OpenAI compatibility
        if not api_base.endswith("/v1"):
            api_base = f"{api_base}/v1" if not api_base.endswith("/") else f"{api_base}v1"

        model_url = f"{api_base}/models/{model_name}"

        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = requests.get(model_url, headers=headers, timeout=10)
            response.raise_for_status()

            model_data = response.json()
            return model_data
        except Exception as e:
            self.logger.error(f"Error fetching model info for {model_name}: {e}")
            return None
