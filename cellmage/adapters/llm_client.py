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

