"""
Token counting utilities for estimating token usage in LLM prompts.

This module provides functions for accurately counting tokens using tiktoken
or falling back to heuristic methods when tiktoken is not available.
"""

import logging
import os
from typing import Any, Dict, List, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Flag to check if tiktoken is available
_TIKTOKEN_AVAILABLE = False
try:
    import tiktoken

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    logger.info("tiktoken package not available, using heuristic token counting")

# Constants
DEFAULT_ENCODING_NAME = "cl100k_base"  # Default for GPT-4, GPT-3.5-turbo models
DEFAULT_TOKENS_PER_WORD = 1.3  # Heuristic: average tokens per word
DEFAULT_CHARS_PER_TOKEN = 4.0  # Heuristic: average characters per token
DEFAULT_TRUNCATE_THRESHOLD = 100000  # Truncate content for safety when calling tiktoken


class TokenCounter:
    """
    A configurable token counting utility for accurate token estimation.

    Provides methods to count tokens in text, code, and structured data,
    with fallbacks for when tiktoken is unavailable.
    """

    def __init__(
        self,
        encoding_name: Optional[str] = None,
        tokens_per_word: Optional[float] = None,
        chars_per_token: Optional[float] = None,
        use_tiktoken: Optional[bool] = None,
    ):
        """
        Initialize the token counter with configurable parameters.

        Args:
            encoding_name: The tiktoken encoding name (model) to use
            tokens_per_word: Average number of tokens per word for heuristic counting
            chars_per_token: Average characters per token for heuristic counting
            use_tiktoken: Force use or non-use of tiktoken regardless of availability
        """
        # Get parameters from environment variables or use defaults
        self.encoding_name = encoding_name or os.getenv(
            "CELLMAGE_TOKEN_ENCODING", DEFAULT_ENCODING_NAME
        )
        self.tokens_per_word = tokens_per_word or float(
            os.getenv("CELLMAGE_TOKENS_PER_WORD", DEFAULT_TOKENS_PER_WORD)
        )
        self.chars_per_token = chars_per_token or float(
            os.getenv("CELLMAGE_CHARS_PER_TOKEN", DEFAULT_CHARS_PER_TOKEN)
        )

        # Determine whether to use tiktoken
        env_use_tiktoken = os.getenv("CELLMAGE_USE_TIKTOKEN")
        if use_tiktoken is not None:
            self.use_tiktoken = use_tiktoken
        elif env_use_tiktoken is not None:
            self.use_tiktoken = env_use_tiktoken.lower() in ("true", "1", "yes")
        else:
            self.use_tiktoken = _TIKTOKEN_AVAILABLE

        # Initialize tiktoken encoder if available and enabled
        self._encoder = None
        if self.use_tiktoken and _TIKTOKEN_AVAILABLE:
            try:
                self._encoder = tiktoken.get_encoding(self.encoding_name)
                logger.debug(f"Initialized tiktoken with encoding: {self.encoding_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken encoding {self.encoding_name}: {e}")
                self.use_tiktoken = False

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string using tiktoken or fallback to heuristic.

        Args:
            text: The text to count tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        if self.use_tiktoken and self._encoder:
            try:
                # Truncate very long text for safety with tiktoken
                if len(text) > DEFAULT_TRUNCATE_THRESHOLD:
                    logger.warning(f"Truncating text of length {len(text)} for token counting")
                    text = text[:DEFAULT_TRUNCATE_THRESHOLD]
                return len(self._encoder.encode(text))
            except Exception as e:
                logger.warning(f"Error using tiktoken to count tokens: {e}")
                # Fall back to heuristic

        # Heuristic counting methods
        words = len(text.split())
        return int(words * self.tokens_per_word)

    def count_tokens_by_chars(self, text: str) -> int:
        """
        Count tokens based on character count (useful for code).

        Args:
            text: The text to count tokens for

        Returns:
            Estimated token count based on character ratio
        """
        if not text:
            return 0

        if self.use_tiktoken and self._encoder:
            try:
                # Truncate very long text for safety with tiktoken
                if len(text) > DEFAULT_TRUNCATE_THRESHOLD:
                    logger.warning(f"Truncating text of length {len(text)} for token counting")
                    text = text[:DEFAULT_TRUNCATE_THRESHOLD]
                return len(self._encoder.encode(text))
            except Exception as e:
                logger.warning(f"Error using tiktoken to count tokens: {e}")
                # Fall back to heuristic

        # Heuristic based on character count
        return int(len(text) / self.chars_per_token)

    def count_tokens_in_dict(self, data: Dict[str, Any], max_depth: int = 5) -> int:
        """
        Count tokens in a dictionary, including nested structures.

        Args:
            data: The dictionary to count tokens for
            max_depth: Maximum recursion depth to prevent stack overflow

        Returns:
            Estimated token count
        """
        if not data or max_depth <= 0:
            return 0

        # Convert to string and count
        if self.use_tiktoken and self._encoder:
            try:
                # Use a more accurate representation for tiktoken
                token_count = 0

                # Count keys and values separately
                for k, v in data.items():
                    # Count the key
                    token_count += self.count_tokens(str(k))

                    # Count the value based on type
                    if isinstance(v, dict):
                        token_count += self.count_tokens_in_dict(v, max_depth - 1)
                    elif isinstance(v, (list, tuple, set)):
                        token_count += self.count_tokens_in_list(v, max_depth - 1)
                    else:
                        token_count += self.count_tokens(str(v))

                # Add tokens for structural elements (brackets, commas)
                token_count += 2  # For the {} braces
                if len(data) > 1:
                    token_count += len(data) - 1  # For commas between items

                return token_count
            except Exception as e:
                logger.warning(f"Error using tiktoken to count tokens in dictionary: {e}")

        # Fallback heuristic: convert to string and count
        text = str(data)
        return self.count_tokens(text)

    def count_tokens_in_list(self, data: List[Any], max_depth: int = 5) -> int:
        """
        Count tokens in a list, including nested structures.

        Args:
            data: The list to count tokens for
            max_depth: Maximum recursion depth to prevent stack overflow

        Returns:
            Estimated token count
        """
        if not data or max_depth <= 0:
            return 0

        if self.use_tiktoken and self._encoder:
            try:
                token_count = 0

                # Count each item
                for item in data:
                    if isinstance(item, dict):
                        token_count += self.count_tokens_in_dict(item, max_depth - 1)
                    elif isinstance(item, (list, tuple, set)):
                        token_count += self.count_tokens_in_list(item, max_depth - 1)
                    else:
                        token_count += self.count_tokens(str(item))

                # Add tokens for structural elements (brackets, commas)
                token_count += 2  # For the [] brackets
                if len(data) > 1:
                    token_count += len(data) - 1  # For commas between items

                return token_count
            except Exception as e:
                logger.warning(f"Error using tiktoken to count tokens in list: {e}")

        # Fallback heuristic: convert to string and count
        text = str(data)
        return self.count_tokens(text)

    def count_tokens_in_code(self, code: str) -> int:
        """
        Count tokens in code content, optimized for source code.

        Args:
            code: The source code text

        Returns:
            Estimated token count
        """
        if not code:
            return 0

        # Code typically has special token patterns, so use char-based heuristic if tiktoken fails
        if self.use_tiktoken and self._encoder:
            try:
                # Truncate very long text for safety with tiktoken
                if len(code) > DEFAULT_TRUNCATE_THRESHOLD:
                    logger.warning(f"Truncating code of length {len(code)} for token counting")
                    code = code[:DEFAULT_TRUNCATE_THRESHOLD]
                return len(self._encoder.encode(code))
            except Exception as e:
                logger.warning(f"Error using tiktoken to count tokens in code: {e}")

        # Fallback for code: character-based heuristic works better than word-based for code
        return self.count_tokens_by_chars(code)


# Create a global instance with default configuration
default_token_counter = TokenCounter()


def count_tokens(text: str) -> int:
    """
    Count tokens in text using the default token counter.

    Args:
        text: The text to count tokens for

    Returns:
        Estimated token count
    """
    return default_token_counter.count_tokens(text)


def count_tokens_in_code(code: str) -> int:
    """
    Count tokens in code using the default token counter.

    Args:
        code: The source code to count tokens for

    Returns:
        Estimated token count
    """
    return default_token_counter.count_tokens_in_code(code)


def count_tokens_in_dict(data: Dict[str, Any]) -> int:
    """
    Count tokens in a dictionary using the default token counter.

    Args:
        data: The dictionary to count tokens for

    Returns:
        Estimated token count
    """
    return default_token_counter.count_tokens_in_dict(data)


def count_tokens_in_list(data: List[Any]) -> int:
    """
    Count tokens in a list using the default token counter.

    Args:
        data: The list to count tokens for

    Returns:
        Estimated token count
    """
    return default_token_counter.count_tokens_in_list(data)
