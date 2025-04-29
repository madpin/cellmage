"""
Example of using the token counting utilities in CellMage.

This script demonstrates how to use the token counter for various types
of content with both tiktoken-based and heuristic counting methods.
"""

import os
import sys

# Add the parent directory to sys.path to import cellmage
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the token utilities
from cellmage.utils.token_utils import TokenCounter, count_tokens, count_tokens_in_code

# Sample content to count tokens for
TEXT_SAMPLE = """
This is a sample text that demonstrates token counting.
Tokens are usually parts of words, punctuation, or special characters.
In most LLM tokenizers, a token is roughly 4 characters long on average.
"""

CODE_SAMPLE = """
def calculate_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

# Example usage
result = calculate_fibonacci(10)
print(f"The 10th Fibonacci number is: {result}")
"""

DICT_SAMPLE = {
    "user": "john_doe",
    "preferences": {"theme": "dark", "notifications": True, "language": "en-US"},
    "activity": [
        {"type": "login", "timestamp": "2023-04-29T14:35:12Z"},
        {"type": "post_created", "timestamp": "2023-04-29T14:40:33Z"},
        {"type": "logout", "timestamp": "2023-04-29T16:12:45Z"},
    ],
}


def main():
    print("CellMage Token Counting Example\n")

    # 1. Using the default token counter via helper functions
    print("Default token counter:")
    print(f"Text sample: {count_tokens(TEXT_SAMPLE)} tokens")
    print(f"Code sample: {count_tokens_in_code(CODE_SAMPLE)} tokens")
    print(f"Dict sample: {count_tokens_in_dict(DICT_SAMPLE)} tokens")

    # 2. Creating a custom token counter with tiktoken
    print("\nCustom token counter with tiktoken (if available):")
    tiktoken_counter = TokenCounter(encoding_name="cl100k_base", use_tiktoken=True)
    print(f"Text sample: {tiktoken_counter.count_tokens(TEXT_SAMPLE)} tokens")
    print(f"Code sample: {tiktoken_counter.count_tokens_in_code(CODE_SAMPLE)} tokens")

    # 3. Creating a custom token counter with heuristic counting
    print("\nCustom token counter with heuristic counting:")
    heuristic_counter = TokenCounter(
        tokens_per_word=1.5,  # Custom tokens per word ratio
        chars_per_token=3.5,  # Custom chars per token ratio
        use_tiktoken=False,  # Force heuristic counting
    )
    print(f"Text sample: {heuristic_counter.count_tokens(TEXT_SAMPLE)} tokens")
    print(f"Code sample: {heuristic_counter.count_tokens_in_code(CODE_SAMPLE)} tokens")

    # 4. Environment variable configuration example
    print("\nTo configure token counting via environment variables:")
    print("export CELLMAGE_TOKEN_ENCODING=cl100k_base")
    print("export CELLMAGE_TOKENS_PER_WORD=1.4")
    print("export CELLMAGE_CHARS_PER_TOKEN=4.2")
    print("export CELLMAGE_USE_TIKTOKEN=true")


if __name__ == "__main__":
    # Import here to avoid circular imports in the example
    from cellmage.utils.token_utils import count_tokens_in_dict

    main()
