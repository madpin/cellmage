#!/usr/bin/env python
"""
Example script showing how to use both DirectLLMAdapter and LangChainAdapter.

This example demonstrates how to initialize and use both adapter implementations
for CellMage, allowing you to compare their behavior and functionality.

Usage:
    python adapter_comparison_example.py

Requirements:
    - Set OPENAI_API_KEY or CELLMAGE_API_KEY environment variable
    - For LangChain adapter, install: pip install "cellmage[langchain]"
"""

import logging
import os
from typing import List

from cellmage.adapters.direct_client import DirectLLMAdapter
from cellmage.models import Message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_adapter(name: str, adapter, prompts: List[str], stream: bool = False):
    """Test an adapter with a series of prompts."""
    print(f"\n{'-' * 20} Testing {name} {'-' * 20}")

    # Display adapter details
    if hasattr(adapter, "__class__"):
        print(f"Adapter type: {adapter.__class__.__name__}")

    # Get adapter overrides
    overrides = adapter.get_overrides()
    model_name = overrides.get("model", "unknown")
    print(f"Using model: {model_name}")

    # Process each prompt
    for i, prompt in enumerate(prompts, 1):
        print(f"\nPrompt {i}: {prompt}")
        print("-" * 40)

        # Create message object
        messages = [Message(role="user", content=prompt)]

        try:
            # Call the adapter
            if stream:
                print("Response (streaming):")

                def print_token(token: str):
                    print(token, end="", flush=True)

                response = adapter.chat(messages=messages, stream=True, stream_callback=print_token)
                print()  # Add newline after streaming
            else:
                response = adapter.chat(messages=messages)
                print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")

    print(f"{'-' * 20} End of {name} Test {'-' * 20}\n")


def main():
    """Run example tests for both adapters."""
    # Check for API key
    api_key = os.environ.get("CELLMAGE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Please set CELLMAGE_API_KEY or OPENAI_API_KEY environment variable")
        return

    # Test prompts
    prompts = ["What is the capital of France?", "Write a short limerick about programming."]

    # Initialize Direct Adapter
    direct_adapter = DirectLLMAdapter(api_key=api_key, default_model="gpt-4.1-nano")

    # Test Direct Adapter without streaming
    test_adapter("Direct Adapter", direct_adapter, prompts, stream=False)

    # Test Direct Adapter with streaming
    test_adapter("Direct Adapter (Streaming)", direct_adapter, prompts, stream=True)

    # Try to initialize LangChain Adapter
    try:
        from cellmage.adapters.langchain_client import LangChainAdapter

        langchain_adapter = LangChainAdapter(api_key=api_key, default_model="gpt-4.1-nano")

        # Test LangChain Adapter without streaming
        test_adapter("LangChain Adapter", langchain_adapter, prompts, stream=False)

        # Test LangChain Adapter with streaming
        test_adapter("LangChain Adapter (Streaming)", langchain_adapter, prompts, stream=True)

    except ImportError:
        print("\nLangChain adapter not available.")
        print("To use the LangChain adapter, install the required dependencies:")
        print('pip install "cellmage[langchain]"')


if __name__ == "__main__":
    main()
