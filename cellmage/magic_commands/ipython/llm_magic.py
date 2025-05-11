"""
Core LLM magic commands for CellMage.

This module provides the %%llm cell magic for sending prompts to LLMs.
"""

import sys
import time
import uuid

from IPython.core.magic import cell_magic, magics_class
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

from cellmage.magic_commands.core import extract_metadata_for_status

from ...context_providers.ipython_context_provider import get_ipython_context_provider
from ...models import Message
from .common import _IPYTHON_AVAILABLE, IPythonMagicsBase, logger


@magics_class
class CoreLLMMagics(IPythonMagicsBase):
    """Core LLM magic commands for CellMage.

    Provides the %%llm cell magic for sending prompts to an LLM.
    """

    @magic_arguments()
    @argument("-p", "--persona", type=str, help="Use specific persona for THIS call only.")
    @argument("-m", "--model", type=str, help="Use specific model for THIS call only.")
    @argument("-t", "--temperature", type=float, help="Set temperature for THIS call.")
    @argument("--max-tokens", type=int, dest="max_tokens", help="Set max_tokens for THIS call.")
    @argument(
        "--no-history",
        action="store_false",
        dest="add_to_history",
        help="Do not add this exchange to history.",
    )
    @argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        help="Do not stream output (wait for full response).",
    )
    @argument(
        "--no-rollback",
        action="store_false",
        dest="auto_rollback",
        help="Disable auto-rollback check for this cell run.",
    )
    @argument(
        "--param",
        nargs=2,
        metavar=("KEY", "VALUE"),
        action="append",
        help="Set any other LLM param ad-hoc (e.g., --param top_p 0.9).",
    )
    @argument("--list-snippets", action="store_true", help="List available snippet names.")
    @argument(
        "--snippet",
        type=str,
        action="append",
        help="Add user snippet content before sending prompt. Can be used multiple times.",
    )
    @argument(
        "--sys-snippet",
        type=str,
        action="append",
        help="Add system snippet content before sending prompt. Can be used multiple times.",
    )
    @cell_magic("llm")
    def execute_llm(self, line, cell):
        """Send the cell content as a prompt to the LLM, applying arguments."""
        if not _IPYTHON_AVAILABLE:
            return

        start_time = time.time()
        status_info = {"success": False, "duration": 0.0}
        context_provider = get_ipython_context_provider()

        try:
            args = parse_argstring(self.execute_llm, line)
            manager = self._get_manager()
        except Exception as e:
            print(f"Error parsing arguments: {e}")
            status_info["duration"] = time.time() - start_time
            context_provider.display_status(status_info)
            return

        # Check if the persona exists if one was specified
        temp_persona = None
        if args.persona:
            # Check if persona exists
            logger.info(f"DEBUG: Checking for persona '{args.persona}'")
            if manager.persona_loader and manager.persona_loader.get_persona(args.persona):
                temp_persona = manager.persona_loader.get_persona(args.persona)
                print(f"Using persona: {args.persona} for this request only")
                logger.info(f"DEBUG: Successfully loaded persona '{args.persona}'")

                # If using an external persona (starts with / or .), ensure its system message is added
                # and it's the first system message
                if (
                    (args.persona.startswith("/") or args.persona.startswith("."))
                    and temp_persona is not None
                    and getattr(temp_persona, "system_message", None)
                ):
                    logger.info(f"Using external file persona: {args.persona}")

                    # Get current history
                    current_history = manager.get_history()

                    # Extract system and non-system messages
                    system_messages = [m for m in current_history if m.role == "system"]
                    non_system_messages = [m for m in current_history if m.role != "system"]

                    # Clear the history
                    manager.clear_history(keep_system=False)

                    # Add persona system message first
                    manager.conversation_manager.add_message(
                        Message(
                            role="system", content=temp_persona.system_message, id=str(uuid.uuid4())
                        )
                    )

                    # Re-add all existing system messages
                    for msg in system_messages:
                        manager.conversation_manager.add_message(msg)

                    # Re-add all non-system messages
                    for msg in non_system_messages:
                        manager.conversation_manager.add_message(msg)
            else:
                # If persona not found, log available personas and warn the user
                available_personas = (
                    manager.list_personas() if hasattr(manager, "list_personas") else []
                )
                logger.info(f"DEBUG: Available personas: {available_personas}")
                print(f"❌ Error: Persona '{args.persona}' not found.")
                print("  To list available personas, use: %llm_config --list-personas")
                status_info["duration"] = time.time() - start_time
                context_provider.display_status(status_info)
                return

        prompt = cell.strip()
        if not prompt:
            print("⚠️ LLM prompt is empty, skipping.")
            status_info["duration"] = time.time() - start_time
            context_provider.display_status(status_info)
            return

        # Handle snippets
        try:
            # Import config handlers for snippet processing
            from .config_handlers.snippet_config_handler import SnippetConfigHandler

            # Initialize the snippet handler and use it directly
            snippet_handler = SnippetConfigHandler()
            snippet_handler.handle_args(args, manager)
        except Exception as e:
            print(f"❌ Unexpected error processing snippets: {e}")
            status_info["duration"] = time.time() - start_time
            context_provider.display_status(status_info)
            return

        # Prepare runtime params
        runtime_params = self._prepare_runtime_params(args)

        # Handle model override
        original_model = None
        if args.model:
            # Directly set model override in the LLM client to ensure highest priority
            if (
                hasattr(manager, "llm_client")
                and manager.llm_client is not None
                and hasattr(manager.llm_client, "set_override")
            ):
                # Temporarily set model override for this call
                original_model = manager.llm_client.get_overrides().get("model")
                manager.llm_client.set_override("model", args.model)
                logger.debug(f"Temporarily set model override to: {args.model}")
            else:
                # Fallback if direct override not possible
                runtime_params["model"] = args.model

        # Debug logging
        logger.debug(f"Sending message with prompt: '{prompt[:50]}...'")
        logger.debug(f"Runtime params: {runtime_params}")

        try:
            # Call the ChatManager's chat method
            result = manager.chat(
                prompt=prompt,
                persona_name=args.persona if args.persona else None,
                model=args.model if args.model else None,
                stream=args.stream,
                add_to_history=args.add_to_history,
                auto_rollback=args.auto_rollback,
                **runtime_params,
            )

            # If we temporarily overrode the model, restore the original value
            if (
                args.model
                and hasattr(manager, "llm_client")
                and manager.llm_client is not None
                and hasattr(manager.llm_client, "set_override")
            ):
                if original_model is not None:
                    manager.llm_client.set_override("model", original_model)
                    logger.debug(f"Restored original model override: {original_model}")
                elif hasattr(manager.llm_client, "remove_override"):
                    manager.llm_client.remove_override("model")
                    logger.debug("Removed temporary model override")

            # If result is successful, mark as success and collect status info
            if result:
                status_info["success"] = True
                status_info["response_content"] = result
                try:
                    history = manager.get_history()
                    from cellmage.magic_commands.core import get_last_assistant_metadata

                    last_meta = get_last_assistant_metadata(history)
                    status_info.update(extract_metadata_for_status(last_meta))
                except Exception as e:
                    logger.error(f"Error extracting metadata for status bar: {e}")

        except Exception as e:
            print(f"❌ LLM Error: {e}", file=sys.stderr)
            logger.error(f"Error during LLM call: {e}")
            status_info["response_content"] = f"Error: {str(e)}"

            # Make sure to restore model override even on error
            if (
                args.model
                and hasattr(manager, "llm_client")
                and manager.llm_client is not None
                and hasattr(manager.llm_client, "set_override")
            ):
                if original_model is not None:
                    manager.llm_client.set_override("model", original_model)
                elif hasattr(manager.llm_client, "remove_override"):
                    manager.llm_client.remove_override("model")
                logger.debug("Restored model override after error")
        finally:
            status_info["duration"] = time.time() - start_time
            # Always ensure model_used is present for the status bar
            if "model_used" not in status_info:
                status_info["model_used"] = status_info.get("model", "")
            context_provider.display_status(status_info)

        return None
