import os
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple, Callable, Union

# Try importing necessary LLM libraries
try:
    import litellm
    from litellm.types import ChatMessage as LiteLLMChatMessage
    _LITELLM_AVAILABLE = True
except ImportError:
    _LITELLM_AVAILABLE = False
    
try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_community.chat_models import ChatLiteLLM
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False

from ..interfaces import LLMClientInterface, StreamCallbackHandler
from ..models import Message
from ..exceptions import LLMInteractionError, ConfigurationError

class LiteLLMAdapter(LLMClientInterface):
    """
    Adapter for LiteLLM that implements the LLMClientInterface.
    
    This adapter supports both direct LiteLLM calls and using LangChain's
    ChatLiteLLM implementation when available.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        default_model: Optional[str] = None
    ):
        """
        Initialize the LiteLLM adapter.
        
        Args:
            api_key: API key for the LLM service, falls back to CELLMAGE_API_KEY env var
            api_base: Base URL for the LLM API, falls back to CELLMAGE_API_BASE env var
            default_model: Default model to use if not specified elsewhere
        """
        if not _LITELLM_AVAILABLE:
            raise ConfigurationError(
                "LiteLLM is required but not installed. Install with: pip install litellm"
            )
        
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
        """Set an instance-level override for LiteLLM parameters."""
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
        Ensure the model name includes a provider prefix if needed.
        This helps LiteLLM properly identify which provider to use.
        
        Args:
            model_name: The model name to check and possibly modify
            
        Returns:
            The model name with provider prefix if needed, or None if input is None
        """
        if not model_name:
            return None
            
        # Common provider prefixes that LiteLLM recognizes
        known_prefixes = [
            "openai/", "anthropic/", "google/", "azure/", "claude/",
            "gpt/", "text/", "llama/", "mistral/", "gemini/"
        ]
        
        # Check if model already has a recognized provider prefix
        if any(model_name.startswith(prefix) for prefix in known_prefixes):
            return model_name
            
        # Some models like gpt-4, gpt-3.5-turbo don't need prefixes
        # LiteLLM will assume OpenAI for these
        if not any(model_name.startswith(prefix) for prefix in known_prefixes):
            model_name = "openai/" + model_name
            
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
        
        # Ensure the model has a provider prefix if needed
        final_model = self._ensure_model_has_provider(final_model)
        
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
            
            # Use LangChain if available (preferred method)
            if _LANGCHAIN_AVAILABLE:
                return self._chat_with_langchain(
                    messages=messages,
                    model=final_model,
                    stream=stream,
                    stream_callback=stream_callback,
                    **final_config
                )
            
            # Fallback to direct LiteLLM if LangChain not available
            return self._chat_with_litellm(
                messages=messages,
                model=final_model,
                stream=stream,
                stream_callback=stream_callback,
                **final_config
            )
            
        except litellm.exceptions.AuthenticationError as e:
            self.logger.error(f"Authentication error: {e}")
            raise LLMInteractionError(f"Authentication failed: {e}")
        except litellm.exceptions.APIConnectionError as e:
            self.logger.error(f"API connection error: {e}")
            raise LLMInteractionError(f"Connection failed: {e}")
        except litellm.exceptions.BadRequestError as e:
            self.logger.error(f"Bad request: {e}")
            raise LLMInteractionError(f"Bad request: {e}")
        except litellm.exceptions.RateLimitError as e:
            self.logger.error(f"Rate limit exceeded: {e}")
            raise LLMInteractionError(f"Rate limit exceeded: {e}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during chat: {e}")
            raise LLMInteractionError(f"Unexpected error: {e}")
    
    def _convert_to_langchain_messages(self, messages: List[Message]) -> List[Any]:
        """Convert our Message format to LangChain message objects."""
        if not _LANGCHAIN_AVAILABLE:
            raise ConfigurationError("LangChain is not available")
            
        converted_messages = []
        for msg in messages:
            if msg.role == "system":
                converted_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                converted_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                converted_messages.append(AIMessage(content=msg.content))
        return converted_messages
    
    def _chat_with_langchain(
        self, 
        messages: List[Message],
        model: str,
        stream: bool,
        stream_callback: Optional[StreamCallbackHandler],
        **kwargs
    ) -> str:
        """Use LangChain's ChatLiteLLM for interaction."""
        # Get API key and base from kwargs or config
        api_key = kwargs.pop("api_key", self._instance_overrides.get("api_key"))
        api_base = kwargs.pop("api_base", self._instance_overrides.get("api_base"))
        
        llm_kwargs = {}
        if api_key:
            llm_kwargs["api_key"] = api_key
        if api_base:
            llm_kwargs["api_base"] = api_base
            
        # Add any remaining kwargs
        llm_kwargs.update(kwargs)
        
        # Convert messages to LangChain format
        lc_messages = self._convert_to_langchain_messages(messages)
        
        # Create chat model
        chat_model = ChatLiteLLM(model=model, **llm_kwargs)
        
        if stream:
            full_response = ""
            for chunk in chat_model.stream(lc_messages):
                content_chunk = chunk.content or ""
                full_response += content_chunk
                
                if stream_callback and content_chunk:
                    stream_callback(content_chunk)
                    
            return full_response.strip()
        else:
            response = chat_model.invoke(lc_messages)
            return response.content.strip() if response and hasattr(response, "content") else ""
    
    def _convert_to_litellm_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert our Message objects to the format LiteLLM expects."""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def _chat_with_litellm(
        self, 
        messages: List[Message],
        model: str,
        stream: bool,
        stream_callback: Optional[StreamCallbackHandler],
        **kwargs
    ) -> str:
        """Use LiteLLM directly for chat completion."""
        # Convert our messages to LiteLLM format
        litellm_messages = self._convert_to_litellm_messages(messages)
        
        if stream:
            full_response = ""
            for chunk in litellm.completion(
                model=model,
                messages=litellm_messages,
                stream=True,
                **kwargs
            ):
                delta = chunk.choices[0].delta
                content_chunk = delta.get("content", "")
                if content_chunk:
                    full_response += content_chunk
                    if stream_callback:
                        stream_callback(content_chunk)
            return full_response.strip()
        else:
            response = litellm.completion(
                model=model,
                messages=litellm_messages,
                **kwargs
            )
            if response.choices and response.choices[0].message:
                return response.choices[0].message.get("content", "").strip()
            return ""
            
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
            import requests
            
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
        try:
            # Remove 'model' from instance overrides for this call
            config = {k: v for k, v in self._instance_overrides.items() if k != "model"}
            
            model_info = litellm.get_model_info(model=model_name, **config)
            if isinstance(model_info, dict):
                return model_info
            elif model_info:
                return {"info": str(model_info)}
            return None
        except Exception as e:
            self.logger.error(f"Failed to get model info for {model_name}: {e}")
            return None

