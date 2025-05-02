"""
SQLite-backed IPython magic commands for CellMage.

This module provides magic commands for using CellMage with SQLite storage in IPython/Jupyter notebooks.
"""

import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

# IPython imports with fallback handling
try:
    from IPython import get_ipython
    from IPython.core.magic import Magics, cell_magic, line_magic, magics_class
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

    class DummyMagics:
        pass  # Dummy base class

    Magics = DummyMagics  # Type alias for compatibility

from ..ambient_mode import (
    disable_ambient_mode,
    enable_ambient_mode,
    is_ambient_mode_enabled,
)

from ..exceptions import PersistenceError, ResourceNotFoundError
from ..conversation_manager import ConversationManager
from ..context_providers.ipython_context_provider import get_ipython_context_provider
from ..models import Message

# Import magic command modules
from ..magic_commands import core, history, persistence
from ..chat_manager import ChatManager
from ..magic_commands.history import get_conversation_statistics

# Logging setup
logger = logging.getLogger(__name__)


def get_chat_manager():
    """
    Create and return a ChatManager instance.
    This is a fallback function to replace the missing get_chat_manager from chat_manager module.
    """
    from ..context_providers.ipython_context_provider import get_ipython_context_provider
    from ..chat_manager import ChatManager
    
    logger.info("Creating new ChatManager instance")
    context_provider = get_ipython_context_provider()
    return ChatManager(context_provider=context_provider)


@magics_class
class SQLiteCellMagics(Magics):
    """IPython magic commands for interacting with CellMage using SQLite storage."""

    def __init__(self, shell):
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not found. CellMage SQLite magics are disabled.")
            return

        super().__init__(shell)
        self.conversation_manager = None
        self.setup_manager()
        
    def setup_manager(self) -> None:
        """Set up the conversation manager."""
        try:
            # Try to get the chat manager first for compatibility
            chat_manager = get_chat_manager()
            
            # Now create or get the conversation manager
            if self.conversation_manager is None:
                context_provider = get_ipython_context_provider()
                
                # Check if we should migrate from existing chat manager
                if hasattr(chat_manager, "history_manager") and chat_manager.history_manager:
                    # Migrate existing history
                    self.conversation_manager = persistence.migrate_to_sqlite(chat_manager)
                    logger.info("Migrated existing history to SQLite storage")
                else:
                    # Create a new conversation manager
                    self.conversation_manager = ConversationManager(
                        context_provider=context_provider
                    )
                    logger.info("Created new SQLite-backed ConversationManager")
            
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
        print(f"  • Storage type: SQLite")
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
            print(f"  • Most used model: {model_info.get('model')} ({model_info.get('count')} times)")
            
        print("══════════════════════════════════════════════════════════")
        
    def process_cell_as_prompt(self, cell_content: str) -> None:
        """Process a regular code cell as an LLM prompt in ambient mode using SQLite storage."""
        if not _IPYTHON_AVAILABLE:
            return

        # Get the original chat manager as we still need it for the LLM client
        try:
            chat_manager = get_chat_manager()
        except Exception as e:
            print(f"❌ Error getting chat manager for LLM client: {e}", file=sys.stderr)
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
            # Get execution context
            exec_count, cell_id = context_provider.get_execution_context()
            
            # Check for cell rerun and perform rollback if needed
            manager.perform_rollback(cell_id)
            
            # Add user message
            user_message = Message(
                role="user",
                content=prompt,
                execution_count=exec_count,
                cell_id=cell_id,
                id=str(uuid.uuid4())
            )
            manager.add_message(user_message)
            
            # Call the ChatManager's chat method with default settings
            # This is a temporary solution until we fully decouple LLM functionality
            result = chat_manager.chat(
                prompt=prompt,
                persona_name=None,  # Use default persona
                stream=True,  # Default to streaming output
                add_to_history=False,  # We manage history ourselves
                auto_rollback=False,  # We've already done rollback
            )

            # If result is successful, capture the assistant response
            if result:
                status_info["success"] = True
                status_info["response_content"] = result
                
                # Extract metadata from chat_manager's last message
                metadata = {}
                try:
                    chat_history = chat_manager.history_manager.get_history()
                    if chat_history and len(chat_history) > 0:
                        last_msg = chat_history[-1]
                        if last_msg.role == "assistant" and last_msg.metadata:
                            metadata = last_msg.metadata.copy()
                except Exception as e:
                    logger.warning(f"Error extracting metadata from chat history: {e}")
                
                # Create assistant message with the result
                assistant_message = Message(
                    role="assistant",
                    content=result,
                    execution_count=exec_count,
                    cell_id=cell_id,
                    id=str(uuid.uuid4()),
                    metadata=metadata
                )
                manager.add_message(assistant_message)
                
                # Collect token counts for status bar
                tokens_in = metadata.get("tokens_in", 0) or 0
                tokens_out = metadata.get("tokens_out", 0) or 0
                
                status_info["tokens_in"] = float(tokens_in)
                status_info["tokens_out"] = float(tokens_out)
                status_info["cost_str"] = metadata.get("cost_str", "")
                status_info["model_used"] = metadata.get("model_used", "")

        except Exception as e:
            print(f"❌ LLM Error (Ambient Mode): {e}", file=sys.stderr)
            logger.error(f"Error during LLM call in ambient mode: {e}")
            # Add error message to status_info for copying
            status_info["response_content"] = f"Error: {str(e)}"
        finally:
            status_info["duration"] = time.time() - start_time
            # Display status bar
            context_provider.display_status(status_info)

    @magic_arguments()
    @argument("--export", type=str, help="Export conversations to markdown files")
    @argument("--import-md", type=str, help="Import a markdown conversation file into SQLite")
    @argument("--stats", action="store_true", help="Show statistics about stored conversations")
    @argument("--list", action="store_true", help="List all stored conversations")
    @argument("--search", type=str, help="Search conversations by content")
    @argument("--load", type=str, help="Load a specific conversation by ID")
    @argument("--delete", type=str, help="Delete a conversation by ID")
    @argument("--tag", nargs=2, metavar=("ID", "TAG"), help="Add a tag to a conversation")
    @argument("--new", action="store_true", help="Start a new conversation")
    @argument("--status", action="store_true", help="Show current SQLite storage status")
    @line_magic("sqlite")
    def sqlite_config(self, line):
        """Configure and manage SQLite storage for CellMage conversations."""
        try:
            args = parse_argstring(self.sqlite_config, line)
            manager = self._get_manager()
            
            if not manager:
                print("❌ Conversation manager not available")
                return
                
            # Track if any action was performed
            action_taken = False

            # Handle export
            if args.export:
                action_taken = True
                path = persistence.export_conversation_to_markdown(manager, filepath=args.export)
                if path:
                    print("✅ Conversation exported successfully")
                    print(f"  • Saved to: {path}")
                else:
                    print("❌ Failed to export conversation")
                    
            # Handle import
            if args.import_md:
                action_taken = True
                if not os.path.exists(args.import_md):
                    print(f"❌ File not found: {args.import_md}")
                else:
                    success = persistence.import_markdown_to_sqlite(manager, args.import_md)
                    if success:
                        print("✅ Conversation imported successfully")
                        print(f"  • Messages: {len(manager.messages)}")
                    else:
                        print("❌ Failed to import conversation")
                        
            # Handle stats
            if args.stats:
                action_taken = True
                stats = history.get_conversation_statistics(manager)
                if stats:
                    print("══════════════════════════════════════════════════════════")
                    print("  📊 Conversation Statistics")
                    print("══════════════════════════════════════════════════════════")
                    print(f"  • Total conversations: {stats.get('total_conversations', 0)}")
                    print(f"  • Total messages: {stats.get('total_messages', 0)}")
                    
                    if "total_tokens" in stats:
                        print(f"  • Total tokens: {stats.get('total_tokens', 0):,}")
                    
                    if "messages_by_role" in stats:
                        print("  • Messages by role:")
                        for role, count in stats["messages_by_role"].items():
                            print(f"    - {role}: {count}")
                            
                    if "most_used_model" in stats and stats["most_used_model"]:
                        model_info = stats["most_used_model"]
                        print(f"  • Most used model: {model_info.get('model', 'unknown')} ({model_info.get('count', 0)} times)")
                        
                    if "most_active_day" in stats and stats["most_active_day"]:
                        activity = stats["most_active_day"]
                        print(f"  • Most active day: {activity.get('date')} with {activity.get('message_count', 0)} messages")
                    
                    print("══════════════════════════════════════════════════════════")
                else:
                    print("❌ Failed to get conversation statistics")
                    
            # Handle list
            if args.list:
                action_taken = True
                conversations = persistence.list_sqlite_conversations()
                if conversations:
                    print("══════════════════════════════════════════════════════════")
                    print("  📋 Conversations in SQLite Storage")
                    print("══════════════════════════════════════════════════════════")
                    for i, conv in enumerate(conversations):
                        # Create a short summary of each conversation
                        print(f"  {i+1}. {conv.get('name', 'Unnamed')} (ID: {conv.get('id', 'unknown')[:8]}...)")
                        print(f"     Date: {datetime.fromtimestamp(conv.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M') if 'timestamp' in conv else 'unknown'}")
                        print(f"     Messages: {conv.get('message_count', 0)}")
                        if conv.get('model_name'):
                            print(f"     Model: {conv.get('model_name')}")
                        if conv.get('tags'):
                            print(f"     Tags: {', '.join(conv.get('tags', []))}")
                        print()
                    print(f"  Total: {len(conversations)} conversation(s)")
                    print("══════════════════════════════════════════════════════════")
                else:
                    print("  No conversations found in SQLite storage")
                    
            # Handle search
            if args.search:
                action_taken = True
                results = persistence.search_sqlite_conversations(args.search, limit=20)
                if results:
                    print("══════════════════════════════════════════════════════════")
                    print(f"  🔍 Search Results for '{args.search}'")
                    print("══════════════════════════════════════════════════════════")
                    for i, conv in enumerate(results):
                        print(f"  {i+1}. {conv.get('name', 'Unnamed')} (ID: {conv.get('id', 'unknown')[:8]}...)")
                        print(f"     Messages: {conv.get('message_count', 0)}")
                        if 'timestamp' in conv:
                            print(f"     Date: {datetime.fromtimestamp(conv.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M')}")
                        print()
                    print(f"  Found {len(results)} conversation(s)")
                    print("══════════════════════════════════════════════════════════")
                else:
                    print(f"  No conversations found matching '{args.search}'")
                    
            # Handle load
            if args.load:
                action_taken = True
                success = manager.load_conversation(args.load)
                if success:
                    print("══════════════════════════════════════════════════════════")
                    print(f"  ✅ Loaded conversation '{args.load}'")
                    print("══════════════════════════════════════════════════════════")
                    print(f"  • Messages: {len(manager.messages)}")
                    
                    # Show the first few messages as preview
                    if manager.messages:
                        print("  • Preview:")
                        for i, msg in enumerate(manager.messages[:3]):
                            if i >= 3:
                                break
                            preview = msg.content.replace("\n", " ")[:60]
                            if len(preview) < len(msg.content):
                                preview += "..."
                            print(f"    - [{msg.role}] {preview}")
                        if len(manager.messages) > 3:
                            print(f"    - ... and {len(manager.messages) - 3} more messages")
                    
                    print("══════════════════════════════════════════════════════════")
                else:
                    print(f"❌ Failed to load conversation '{args.load}'")
                    
            # Handle delete
            if args.delete:
                action_taken = True
                success = manager.delete_conversation(args.delete)
                if success:
                    print(f"✅ Deleted conversation '{args.delete}'")
                else:
                    print(f"❌ Failed to delete conversation '{args.delete}'")
                    
            # Handle tag
            if args.tag:
                action_taken = True
                conv_id, tag = args.tag
                success = persistence.tag_sqlite_conversation(conv_id, tag)
                if success:
                    print(f"✅ Added tag '{tag}' to conversation '{conv_id}'")
                else:
                    print(f"❌ Failed to add tag '{tag}' to conversation '{conv_id}'")
                    
            # Handle new conversation
            if args.new:
                action_taken = True
                new_id = manager.create_new_conversation()
                print(f"✅ Created new conversation with ID: {new_id}")
                
            # Handle status display
            if args.status or not action_taken:
                self._show_status()
                
        except Exception as e:
            print(f"❌ Error in SQLite command: {e}")
            import traceback
            traceback.print_exc()
            logger.exception(f"Error in SQLite command: {e}")
            
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
            
        # Get the original chat manager as we still need it for the LLM client
        try:
            chat_manager = get_chat_manager()
        except Exception as e:
            print(f"❌ Error getting chat manager for LLM client: {e}", file=sys.stderr)
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
        
        # Add user message
        user_message = Message(
            role="user",
            content=prompt,
            execution_count=exec_count,
            cell_id=cell_id,
            id=str(uuid.uuid4())
        )
        manager.add_message(user_message)
        
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
        if args.model:
            # Temporarily set model override for this call
            if chat_manager.llm_client and hasattr(chat_manager.llm_client, "set_override"):
                original_model = chat_manager.llm_client.get_overrides().get("model")
                chat_manager.llm_client.set_override("model", args.model)
                logger.debug(f"Temporarily set model override to: {args.model}")
            else:
                runtime_params["model"] = args.model

        try:
            # Call the ChatManager's chat method
            result = chat_manager.chat(
                prompt=prompt,
                persona_name=args.persona if hasattr(args, "persona") else None,
                stream=args.stream if hasattr(args, "stream") else True,
                add_to_history=False,  # We manage history ourselves in SQLite
                auto_rollback=False,   # We already handled rollback
                **runtime_params
            )

            # If original model was overridden, restore it
            if args.model and chat_manager.llm_client and hasattr(chat_manager.llm_client, "set_override"):
                if original_model is not None:
                    chat_manager.llm_client.set_override("model", original_model)
                else:
                    chat_manager.llm_client.remove_override("model")

            # If result is successful, capture the assistant response
            if result:
                status_info["success"] = True
                status_info["response_content"] = result
                
                # Extract metadata from chat_manager's last message
                metadata = {}
                try:
                    chat_history = chat_manager.history_manager.get_history()
                    if chat_history and len(chat_history) > 0:
                        last_msg = chat_history[-1]
                        if last_msg.role == "assistant" and last_msg.metadata:
                            metadata = last_msg.metadata.copy()
                except Exception as e:
                    logger.warning(f"Error extracting metadata from chat history: {e}")
                
                # Create assistant message with the result
                assistant_message = Message(
                    role="assistant",
                    content=result,
                    execution_count=exec_count,
                    cell_id=cell_id,
                    id=str(uuid.uuid4()),
                    metadata=metadata
                )
                manager.add_message(assistant_message)
                
                # Collect token counts for status bar
                tokens_in = metadata.get("tokens_in", 0) or 0
                tokens_out = metadata.get("tokens_out", 0) or 0
                
                status_info["tokens_in"] = float(tokens_in)
                status_info["tokens_out"] = float(tokens_out)
                status_info["cost_str"] = metadata.get("cost_str", "")
                status_info["model_used"] = metadata.get("model_used", "")

        except Exception as e:
            print(f"❌ LLM Error: {e}", file=sys.stderr)
            logger.error(f"Error during LLM call: {e}")
            # Add error message to status_info for copying
            status_info["response_content"] = f"Error: {str(e)}"
            
            # Make sure to restore model override even on error
            if args.model and chat_manager.llm_client and hasattr(chat_manager.llm_client, "set_override"):
                if original_model is not None:
                    chat_manager.llm_client.set_override("model", original_model)
                else:
                    chat_manager.llm_client.remove_override("model")
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
    """
    Registers the SQLite magics with the IPython runtime.
    """
    if not _IPYTHON_AVAILABLE:
        print("IPython is not available. Cannot load extension.", file=sys.stderr)
        return

    try:
        # Create and register the SQLite magic class
        magic_class = SQLiteCellMagics(ipython)
        ipython.register_magics(magic_class)
        
        # Register the standalone llm magic (alias for sqlite_llm)
        ipython.register_magic_function(llm_magic, magic_kind='cell', magic_name='llm')
        
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
            ipython.run_cell("%config TerminalInteractiveShell.term_title_format='CellMage [SQLite]'")
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
    """Unregisters the magics when the extension is unloaded."""
    if not _IPYTHON_AVAILABLE:
        return
    
    # Disable ambient mode if it's active
    if is_ambient_mode_enabled():
        disable_ambient_mode(ipython)
        
    logger.info("SQLite extension unloaded")