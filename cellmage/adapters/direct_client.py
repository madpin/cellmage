import os
import logging
import json
import uuid
import time
import requests
import threading
from typing import Dict, List, Optional, Any, Tuple, Union
from queue import Queue

from ..interfaces import LLMClientInterface, StreamCallbackHandler
from ..models import Message
from ..exceptions import LLMInteractionError, ConfigurationError

class DirectLLMAdapter(LLMClientInterface):
    """
    Direct HTTP adapter for LLM APIs that implements the LLMClientInterface.
    
    This adapter communicates directly with OpenAI-compatible APIs without using
    the litellm package as a dependency.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        default_model: Optional[str] = None
    ):
        """
        Initialize the Direct LLM adapter.
        
        Args:
            api_key: API key for the LLM service, falls back to CELLMAGE_API_KEY env var
            api_base: Base URL for the LLM API, falls back to CELLMAGE_API_BASE env var
            default_model: Default model to use if not specified elsewhere
        """
        self.logger = logging.getLogger(__name__)
        self._instance_overrides: Dict[str, Any] = {}
        
        # Initialize API credentials from parameters or environment variables
        if api_key:
            self.set_override("api_key", api_key)
        elif "CELLMAGE_API_KEY" in os.environ:
            self.set_override("api_key", os.environ["CELLMAGE_API_KEY"])
            
        if api_base:
            self.set_override("api_base", api_base)
        elif "CELLMAGE_API_BASE" in os.environ:
            self.set_override("api_base", os.environ["CELLMAGE_API_BASE"])
            
        if default_model:
            self.set_override("model", default_model)
        
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
        """Remove all instance-level overrides."""
        self._instance_overrides = {}
        self.logger.info("[Override] All instance overrides cleared.")
        
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
        call_overrides: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Determine the final model and configuration to use.
        
        Args:
            model_name: Model name specified at the call level
            system_message: System message to include
            call_overrides: Additional overrides for this specific call
            
        Returns:
            Tuple of (final_model, final_config)
            
        Raises:
            ConfigurationError: If no valid model can be determined
        """
        # Merge instance overrides with call overrides, with call taking precedence
        final_config = self._instance_overrides.copy()
        final_config.update(call_overrides)
        
        # Determine final model name, with priority:
        # 1. Call overrides
        # 2. Instance overrides
        # 3. Model name passed to this method
        final_model = (
            call_overrides.get("model") or
            self._instance_overrides.get("model") or
            model_name
        )
        
        # Unlike litellm, we don't modify the model name with provider prefixes
        
        if not final_model:
            raise ConfigurationError(
                "No model specified. Provide via model parameter, set_override('model'), "
                "or in the constructor."
            )
            
        # Remove model from config since it's passed separately
        final_config.pop("model", None)
        
        return final_model, final_config
    
    def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        stream: bool = False,
        stream_callback: Optional[StreamCallbackHandler] = None,
        **kwargs
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
            
            self.logger.info(f"Calling model '{final_model}' with {len(messages)} messages")
            
            # Convert our messages to the format expected by the API
            api_messages = self._convert_messages(messages)
            
            # Get base URL and API key
            api_base = final_config.pop("api_base", None)
            if not api_base:
                raise ConfigurationError("API base URL is required but not provided")
                
            api_key = final_config.pop("api_key", None)
            if not api_key:
                raise ConfigurationError("API key is required but not provided")
            
            # Ensure api_base ends with /v1 for OpenAI compatibility
            if not api_base.endswith("/v1"):
                api_base = f"{api_base}/v1" if not api_base.endswith("/") else f"{api_base}v1"
            
            # Create the request payload
            payload = {
                "model": final_model,
                "messages": api_messages,
                "stream": stream,
                **final_config
            }
            
            # Set up the headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            # Make the request
            if stream:
                return self._handle_streaming(
                    api_base, headers, payload, stream_callback
                )
            else:
                return self._handle_non_streaming(
                    api_base, headers, payload
                )
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API connection error: {e}")
            raise LLMInteractionError(f"Connection failed: {e}")
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response: {e}")
            raise LLMInteractionError(f"Invalid response format: {e}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during chat: {e}")
            raise LLMInteractionError(f"Unexpected error: {e}")
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert our Message objects to the format expected by the API."""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def _handle_non_streaming(self, api_base: str, headers: Dict[str, str], payload: Dict[str, Any]) -> str:
        """Handle non-streaming API response."""
        url = f"{api_base}/chat/completions"
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60  # Default timeout of 60 seconds
        )
        
        # Check for errors
        if response.status_code != 200:
            self._handle_error_response(response)
        
        # Parse the response
        result = response.json()
        
        # Extract the assistant's message
        if "choices" in result and len(result["choices"]) > 0:
            if "message" in result["choices"][0]:
                content = result["choices"][0]["message"].get("content", "")
                return content.strip()
        
        return ""
    
    def _handle_streaming(
        self, 
        api_base: str, 
        headers: Dict[str, str], 
        payload: Dict[str, Any],
        stream_callback: Optional[StreamCallbackHandler]
    ) -> str:
        """Handle streaming API response."""
        url = f"{api_base}/chat/completions"
        
        # Set stream to True in the payload
        payload["stream"] = True
        
        # Make the streaming request
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=60  # Default timeout of 60 seconds
        )
        
        # Check for errors
        if response.status_code != 200:
            self._handle_error_response(response)
        
        full_response = ""
        
        # Process the streaming response
        for line in response.iter_lines():
            if line:
                # Remove the "data: " prefix, if present
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    line_text = line_text[6:]  # Remove "data: " prefix
                
                # Skip empty lines or [DONE] marker
                if line_text.strip() == '' or line_text.strip() == '[DONE]':
                    continue
                
                try:
                    chunk = json.loads(line_text)
                    
                    # Extract delta content from the chunk
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        content_chunk = delta.get("content", "")
                        
                        if content_chunk:
                            full_response += content_chunk
                            if stream_callback:
                                stream_callback(content_chunk)
                except json.JSONDecodeError:
                    # Ignore invalid JSON (like the [DONE] marker)
                    pass
        
        return full_response.strip()
    
    def _handle_error_response(self, response: requests.Response) -> None:
        """Handle error responses from the API."""
        try:
            error_info = response.json()
            error_message = error_info.get('error', {}).get('message', 'Unknown error')
            error_type = error_info.get('error', {}).get('type', 'Unknown error type')
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
                self.logger.warning(f"Unexpected response format from models endpoint")
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