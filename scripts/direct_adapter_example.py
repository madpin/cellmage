#!/usr/bin/env python
"""
Example script demonstrating how to use cellmage with DirectLLMAdapter directly.

This script shows how to use the cellmage library without the litellm package,
using the built-in DirectLLMAdapter which communicates directly with OpenAI-compatible APIs.

Usage:
    python direct_adapter_example.py

Requirements:
    - cellmage package installed
    - CELLMAGE_API_KEY environment variable set (or passed via --api-key)
    - CELLMAGE_API_BASE environment variable set (or passed via --api-base)
"""

import argparse
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main(
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    model: str = "gpt-3.5-turbo",
    prompt: str = "Explain what cellmage is and how it helps users interact with LLMs.",
):
    """
    Run a simple example using the DirectLLMAdapter.

    Args:
        api_key: API key for LLM service (falls back to CELLMAGE_API_KEY env var)
        api_base: API base URL (falls back to CELLMAGE_API_BASE env var)
        model: Model to use for the completion
        prompt: Prompt to send to the LLM
    """
    try:
        # Import the DirectLLMAdapter
        import uuid

        from cellmage.adapters.direct_client import DirectLLMAdapter
        from cellmage.models import Message

        # Create the DirectLLMAdapter
        adapter = DirectLLMAdapter(api_key=api_key, api_base=api_base, default_model=model)

        logger.info(f"Created DirectLLMAdapter with model: {model}")

        # Prepare messages
        system_msg = Message(
            role="system",
            content="You are a helpful assistant that provides clear and concise information.",
            id=str(uuid.uuid4()),
        )

        user_msg = Message(role="user", content=prompt, id=str(uuid.uuid4()))

        messages = [system_msg, user_msg]

        # Send the messages to the LLM
        logger.info("Sending request to LLM...")
        response = adapter.chat(
            messages=messages,
            model=model,
            stream=True,  # Enable streaming for a more interactive experience
            stream_callback=lambda chunk: print(
                chunk, end="", flush=True
            ),  # Print chunks as they arrive
        )

        print("\n\n" + "-" * 50)
        logger.info("Complete response:")
        print(response)
        print("-" * 50)

        # You can also use non-streaming mode
        logger.info("Sending another request in non-streaming mode...")
        response = adapter.chat(messages=messages, model=model, stream=False)

        print("\n" + "-" * 50)
        logger.info("Non-streaming response:")
        print(response)
        print("-" * 50)

        # Optional: Get available models if the API supports it
        try:
            logger.info("Fetching available models...")
            models = adapter.get_available_models()
            if models:
                logger.info(f"Available models: {[m.get('id', 'unknown') for m in models[:5]]}...")
            else:
                logger.info("No models returned or API doesn't support model listing")
        except Exception as e:
            logger.error(f"Error fetching models: {e}")

    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Please make sure cellmage is installed: pip install cellmage")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Example script for cellmage DirectLLMAdapter")
    parser.add_argument(
        "--api-key", help="API key for LLM service (falls back to CELLMAGE_API_KEY env var)"
    )
    parser.add_argument("--api-base", help="API base URL (falls back to CELLMAGE_API_BASE env var)")
    parser.add_argument(
        "--model", default="gpt-3.5-turbo", help="Model to use (default: gpt-3.5-turbo)"
    )
    parser.add_argument(
        "--prompt",
        default="Explain what cellmage is and how it helps users interact with LLMs.",
        help="Prompt to send to the LLM",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    main(args.api_key, args.api_base, args.model, args.prompt)
