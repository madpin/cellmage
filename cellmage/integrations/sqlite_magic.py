"""
SQLite-backed IPython magic commands for CellMage.

This module provides magic commands for using CellMage with SQLite storage in IPython/Jupyter notebooks.
"""

import logging
import sys
import time
from typing import List, Optional

# IPython imports with fallback handling
try:
    from IPython.core.magic import cell_magic, line_magic, magics_class
    from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

    # Define dummy decorators if IPython is not installed
    def magics_class(cls):
        return cls

    def line_magic(func):
        return func

    def cell_magic(func):
        return func

    def magic_arguments():
        return lambda func: func

    def argument(*args, **kwargs):
        return lambda func: func


# Import the base magic class
from .base_magic import BaseMagics

# Create a global logger
logger = logging.getLogger(__name__)

# Check if SQLite storage components are available
try:
    from ..ambient_mode import disable_ambient_mode, is_ambient_mode_enabled
    from ..context_providers.ipython_context_provider import (
        get_ipython_context_provider,
    )
    from ..conversation_manager import ConversationManager
    from ..magic_commands import history, persistence

    _SQLITE_AVAILABLE = True
except ImportError:
    _SQLITE_AVAILABLE = False


def get_conversation_manager() -> ConversationManager:
    """
    Get the default conversation manager instance.
    
    Returns:
        A fully configured ConversationManager instance
    """
    from .. import get_default_conversation_manager
    logger.info("Getting default ConversationManager instance")
    return get_default_conversation_manager()


@magics_class
class SQLiteCellMagics(BaseMagics):
    """IPython magic commands for interacting with CellMage using SQLite storage."""

    def __init__(self, shell):
        """Initialize the SQLite magic utility."""
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not found. CellMage SQLite magics are disabled.")
            return

        super().__init__(shell)
        self.conversation_manager = None
        self.setup_manager()

    def setup_manager(self) -> None:
        """Set up the conversation manager."""
        try:
            # Get the conversation manager directly
            if self.conversation_manager is None:
                self.conversation_manager = get_conversation_manager()
                logger.info("Acquired ConversationManager for SQLite magic")

            logger.info("SQLiteCellMagics initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing SQLiteCellMagics: {e}")
            print(f"❌ Error initializing SQLite storage: {e}", file=sys.stderr)

    def _get_manager(self) -> Optional[ConversationManager]:
        """Helper to get the conversation manager instance, with clear error handling."""
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython not available", file=sys.stderr)
            return None

        try:
            if self.conversation_manager is None:
                self.setup_manager()

            return self.conversation_manager
        except Exception as e:
            print("❌ CellMage Error: Could not get Conversation Manager.", file=sys.stderr)
            print(f"   Reason: {e}", file=sys.stderr)
            print(
                "   Please check your configuration (.env file, API keys, directories) and restart the kernel.",
                file=sys.stderr,
            )
            return None

    def _add_to_history(
        self, content: str, source_type: str, source_id: str, as_system_msg: bool = False
    ) -> bool:
        """Add the content to the chat history as a user or system message."""
        return super()._add_to_history(
            content=content,
            source_type=source_type,
            source_id=source_id,
            source_name="sqlite",
            id_key="sqlite_id",
            as_system_msg=as_system_msg,
        )

    def _find_messages_to_remove(
        self, history: List, source_name: str, source_type: str, source_id: str, id_key: str
    ) -> List[int]:
        """
        Find messages to remove from history based on SQLite-specific rules.

        Remove previous messages with the same source type and ID.
        """
        indices_to_remove = []

        # Match by source type and ID
        for i, msg in enumerate(history):
            if (
                msg.metadata
                and msg.metadata.get("source") == source_name
                and msg.metadata.get("type") == source_type
                and msg.metadata.get(id_key) == source_id
            ):
                indices_to_remove.append(i)

        return indices_to_remove

    def _show_status(self) -> None:
        """Show current SQLite storage status."""
        manager = self._get_manager()
        if not manager:
            print("❌ Conversation manager not available")
            return

        # Get statistics using the history module function
        stats = history.get_conversation_statistics(manager)

        # Print stats
        print("══════════════════════════════════════════════════════════")
        print("  🗄️  SQLite Storage Status")
        print("══════════════════════════════════════════════════════════")
        print("  • Storage type: SQLite")
        print(f"  • Current conversation ID: {manager.current_conversation_id}")
        print(f"  • Current message count: {len(manager.messages)}")
        print(f"  • Total conversations: {stats.get('total_conversations', 0)}")
        print(f"  • Total messages: {stats.get('total_messages', 0)}")

        # Add token stats if available
        if "total_tokens" in stats:
            print(f"  • Total tokens: {stats.get('total_tokens', 0):,}")

        # Show models if available
        if "most_used_model" in stats and stats["most_used_model"]:
            model_info = stats["most_used_model"]
            print(
                f"  • Most used model: {model_info.get('model')} ({model_info.get('count')} times)"
            )

        print("══════════════════════════════════════════════════════════")

    def process_cell_as_prompt(self, cell_content: str) -> None:
        """Process a regular code cell as an LLM prompt in ambient mode using SQLite storage."""
        if not _IPYTHON_AVAILABLE:
            return

        # Get the conversation manager
        manager = self._get_manager()
        if not manager:
            print("❌ Conversation manager not available", file=sys.stderr)
            return

        start_time = time.time()
        status_info = {"success": False, "duration": 0.0}
        context_provider = get_ipython_context_provider()

        prompt = cell_content.strip()
        if not prompt:
            logger.debug("Skipping empty prompt in ambient mode.")
            return

        logger.debug(f"Processing cell as prompt in ambient mode: '{prompt[:50]}...'")

        try:
            # Get execution context for cell identification
            exec_count, cell_id = context_provider.get_execution_context()

            # Check for cell rerun and perform rollback if needed
            manager.perform_rollback(cell_id)

            try:
                # Call the ConversationManager's chat method directly
                result = manager.chat(
                    prompt=prompt,
                    persona_name=None,  # Use default persona
                    stream=True,        # Default to streaming output
                    add_to_history=True, # Let ConversationManager handle the history
                )

                # If result is successful, update status info
                if result:
                    status_info["success"] = True
                    status_info["response_content"] = result

                    # Get the last assistant message for metadata
                    for msg in reversed(manager.messages):
                        if msg.role == "assistant" and msg.metadata:
                            # Collect token counts for status bar
                            tokens_in = msg.metadata.get("tokens_in", 0) or 0
                            tokens_out = msg.metadata.get("tokens_out", 0) or 0

                            status_info["tokens_in"] = float(tokens_in)
                            status_info["tokens_out"] = float(tokens_out)
                            status_info["cost_str"] = msg.metadata.get("cost_str", "")
                            status_info["model_used"] = msg.metadata.get("model_used", "")
                            break

            except Exception as e:
                print(f"❌ LLM Error (Ambient Mode): {e}", file=sys.stderr)
                logger.error(f"Error during LLM call in ambient mode: {e}")
                # Add error message to status_info for copying
                status_info["response_content"] = f"Error: {str(e)}"
        except Exception as e:
            print(f"❌ Error in ambient mode: {e}", file=sys.stderr)
            logger.error(f"Error in ambient mode: {e}")
        finally:
            status_info["duration"] = time.time() - start_time
            # Display status bar
            context_provider.display_status(status_info)

    @magic_arguments()
    @argument("-p", "--persona", type=str, help="Use specific persona for THIS call only.")
    @argument("-m", "--model", type=str, help="Use specific model for THIS call only.")
    @argument("-t", "--temperature", type=float, help="Set temperature for THIS call.")
    @argument("--max-tokens", type=int, dest="max_tokens", help="Set max_tokens for THIS call.")
    @argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        help="Do not stream output (wait for full response).",
    )
    @argument(
        "--param",
        nargs=2,
        metavar=("KEY", "VALUE"),
        action="append",
        help="Set any other LLM param ad-hoc (e.g., --param top_p 0.9).",
    )
    @cell_magic("sqlite_llm")
    def sqlite_llm_magic(self, line, cell):
        """Send the cell content as a prompt to the LLM, storing history in SQLite."""
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython not available", file=sys.stderr)
            return None

        # Get the conversation manager
        manager = self._get_manager()
        if not manager:
            print("❌ Conversation manager not available", file=sys.stderr)
            return None

        start_time = time.time()
        status_info = {"success": False, "duration": 0.0}
        context_provider = get_ipython_context_provider()

        try:
            args = parse_argstring(self.sqlite_llm_magic, line)
        except Exception as e:
            print(f"❌ Error parsing arguments: {e}", file=sys.stderr)
            status_info["duration"] = time.time() - start_time
            context_provider.display_status(status_info)
            return None

        prompt = cell.strip()
        if not prompt:
            print("⚠️ LLM prompt is empty, skipping.", file=sys.stderr)
            status_info["duration"] = time.time() - start_time
            context_provider.display_status(status_info)
            return None

        # Get execution context
        exec_count, cell_id = context_provider.get_execution_context()

        # Check for cell rerun and perform rollback if needed
        manager.perform_rollback(cell_id)

        # Prepare runtime params
        runtime_params = {}

        # Handle simple parameters
        if hasattr(args, "temperature") and args.temperature is not None:
            runtime_params["temperature"] = args.temperature

        if hasattr(args, "max_tokens") and args.max_tokens is not None:
            runtime_params["max_tokens"] = args.max_tokens

        # Handle arbitrary parameters from --param
        if hasattr(args, "param") and args.param:
            for key, value in args.param:
                # Try to convert string values to appropriate types
                try:
                    # First try to convert to int or float if it looks numeric
                    if "." in value:
                        parsed_value = float(value)
                    else:
                        try:
                            parsed_value = int(value)
                        except ValueError:
                            parsed_value = value
                except ValueError:
                    parsed_value = value

                runtime_params[key] = parsed_value

        # Handle model override
        original_model = None
        if hasattr(args, "model") and args.model:
            if manager.llm_client and hasattr(manager.llm_client, "set_override"):
                original_model = manager.get_overrides().get("model")
                manager.set_override("model", args.model)
                logger.debug(f"Temporarily set model override to: {args.model}")
            else:
                runtime_params["model"] = args.model

        try:
            # Call the ConversationManager's chat method directly
            result = manager.chat(
                prompt=prompt,
                persona_name=args.persona if hasattr(args, "persona") else None,
                model=args.model if hasattr(args, "model") else None,
                stream=args.stream if hasattr(args, "stream") else True,
                add_to_history=True,  # Let ConversationManager handle history
                **runtime_params,
            )

            # If original model was overridden, restore it
            if (
                hasattr(args, "model")
                and args.model
                and manager.llm_client
                and hasattr(manager.llm_client, "set_override")
            ):
                if original_model is not None:
                    manager.set_override("model", original_model)
                else:
                    manager.remove_override("model")

            # If result is successful, capture the assistant response
            if result:
                status_info["success"] = True
                status_info["response_content"] = result

                # Extract metadata from the last message
                for msg in reversed(manager.messages):
                    if msg.role == "assistant" and msg.metadata:
                        # Collect token counts for status bar
                        tokens_in = msg.metadata.get("tokens_in", 0) or 0
                        tokens_out = msg.metadata.get("tokens_out", 0) or 0

                        status_info["tokens_in"] = float(tokens_in)
                        status_info["tokens_out"] = float(tokens_out)
                        status_info["cost_str"] = msg.metadata.get("cost_str", "")
                        status_info["model_used"] = msg.metadata.get("model_used", "")
                        break

        except Exception as e:
            print(f"❌ LLM Error: {e}", file=sys.stderr)
            logger.error(f"Error during LLM call: {e}")
            # Add error message to status_info for copying
            status_info["response_content"] = f"Error: {str(e)}"

            # Make sure to restore model override even on error
            if (
                hasattr(args, "model")
                and args.model
                and manager.llm_client
                and hasattr(manager.llm_client, "set_override")
            ):
                if original_model is not None:
                    manager.set_override("model", original_model)
                else:
                    manager.remove_override("model")
        finally:
            status_info["duration"] = time.time() - start_time
            # Display status bar
            context_provider.display_status(status_info)

        return None


@magic_arguments()
@argument("-p", "--persona", type=str, help="Use specific persona for THIS call only.")
@argument("-m", "--model", type=str, help="Use specific model for THIS call only.")
@argument("-t", "--temperature", type=float, help="Set temperature for THIS call.")
@argument("--max-tokens", type=int, dest="max_tokens", help="Set max_tokens for THIS call.")
@argument("--no-stream", action="store_false", dest="stream", help="Do not stream output.")
@argument("--param", nargs=2, metavar=("KEY", "VALUE"), action="append")
@cell_magic("llm")
def llm_magic(ip, line, cell):
    """Default %%llm magic that uses SQLite storage."""
    if not _IPYTHON_AVAILABLE:
        print("❌ IPython not available", file=sys.stderr)
        return

    # Create magics class instance
    magics = SQLiteCellMagics(ip)

    # Forward to sqlite_llm implementation
    return magics.sqlite_llm_magic(line, cell)


# --- Extension Loading ---
def load_ipython_extension(ipython):
    """Register the SQLite magics with the IPython runtime."""
    if not _IPYTHON_AVAILABLE:
        print("IPython is not available. Cannot load extension.", file=sys.stderr)
        return

    if not _SQLITE_AVAILABLE:
        print(
            "SQLite storage components are not available. Cannot load extension.", file=sys.stderr
        )
        return

    try:
        # Create and register the SQLite magic class
        magic_class = SQLiteCellMagics(ipython)
        ipython.register_magics(magic_class)

        # Register the standalone llm magic (alias for sqlite_llm)
        ipython.register_magic_function(llm_magic, magic_kind="cell", magic_name="llm")

        # Import and register the llm_config line magic from ipython_magic.py
        try:
            from .ipython_magic import NotebookLLMMagics

            notebook_magics = NotebookLLMMagics(ipython)

            # Register the notebook magics class which includes llm_config
            ipython.register_magics(notebook_magics)

            # No need for the warning check that was causing the message
            # Just log that we registered the magics successfully
            logger.info("Registered NotebookLLMMagics class which includes llm_config")

        except Exception as e:
            logger.exception(f"Failed to register llm_config line magic: {e}")
            print(f"❌ Failed to register llm_config line magic: {e}", file=sys.stderr)

        # Update shell page title if possible
        try:
            ipython.run_cell(
                "%config TerminalInteractiveShell.term_title_format='CellMage [SQLite]'"
            )
        except Exception:
            pass  # Not critical if this fails

        # Set ambient mode handlers
        try:
            from ..ambient_mode import register_ambient_handler

            register_ambient_handler(magic_class.process_cell_as_prompt)
            logger.info("Registered SQLite ambient mode handler")
        except Exception as e:
            logger.warning(f"Failed to register ambient mode handler: {e}")

        logger.info("SQLite-backed CellMage extension loaded successfully")
        print("✅ CellMage loaded with SQLite storage (default)", file=sys.stderr)

    except Exception as e:
        logger.exception("Failed to register SQLite magics.")
        print(f"❌ Failed to initialize SQLite magics: {e}", file=sys.stderr)


def unload_ipython_extension(ipython):
    """Unregister the magics when the extension is unloaded."""
    if not _IPYTHON_AVAILABLE:
        return

    # Disable ambient mode if it's active
    try:
        if is_ambient_mode_enabled():
            disable_ambient_mode(ipython)
    except Exception:
        pass  # Not critical if this fails

    logger.info("SQLite extension unloaded")
