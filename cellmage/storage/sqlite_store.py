"""
SQLite-based storage for conversation history.

This module provides a SQLite implementation of the HistoryStore interface
for persisting conversations in a SQLite database.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..config import settings
from ..exceptions import PersistenceError
from ..interfaces import HistoryStore
from ..models import ConversationMetadata, Message


class SQLiteStore(HistoryStore):
    """
    Stores conversation history in a SQLite database.
    Provides advanced querying and debugging capabilities.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Initialize the SQLite storage.

        Args:
            db_path: Path to the SQLite database file. If None, uses config.settings.sqlite_path_resolved.
        """
        self.logger = logging.getLogger(__name__)

        # Always use config.settings.sqlite_path_resolved unless explicitly overridden
        # The resolved path is always based on CELLMAGE_SQLITE_PATH if set, otherwise ${base_dir}/.data/conversations.db
        if db_path is not None:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(settings.sqlite_path_resolved)
        self.logger.info(f"Initializing SQLiteStore with database at: {self.db_path}")
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Create conversations table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    model_name TEXT,
                    persona_name TEXT,
                    timestamp TEXT,
                    saved_at TEXT,
                    total_tokens INTEGER,
                    metadata TEXT
                )
            """
            )

            # Create messages table with foreign key to conversations
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    tokens INTEGER,
                    execution_count INTEGER,
                    cell_id TEXT,
                    position INTEGER,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """
            )

            # Create raw_api_responses table to store the original API responses
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_api_responses (
                    id TEXT PRIMARY KEY,
                    message_id TEXT,
                    conversation_id TEXT,
                    timestamp TEXT,
                    endpoint TEXT,
                    request_data TEXT,
                    response_data TEXT,
                    response_time_ms INTEGER,
                    status_code INTEGER,
                    FOREIGN KEY (message_id) REFERENCES messages (id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """
            )

            # Create tags table for filtering conversations
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tags (
                    conversation_id TEXT,
                    tag TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id),
                    UNIQUE (conversation_id, tag)
                )
            """
            )

            # Create debug_logs table for detailed debugging information
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS debug_logs (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    message_id TEXT,
                    timestamp TEXT,
                    log_level TEXT,
                    component TEXT,
                    event TEXT,
                    details TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id),
                    FOREIGN KEY (message_id) REFERENCES messages (id)
                )
            """
            )

            # Create versions table to track schema versions and migrations
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS versions (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT,
                    description TEXT
                )
            """
            )

            # Insert initial version or update existing version
            cursor.execute(
                """
                INSERT OR REPLACE INTO versions (version, applied_at, description)
                VALUES ('1.2.0', ?, 'Updated schema to use datetime TEXT fields')
            """,
                (datetime.now().isoformat(),),
            )

            # Create indexes for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_role ON messages (role)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_tags_conversation_id ON tags (conversation_id)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags (tag)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_debug_logs_conversation_id ON debug_logs (conversation_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_raw_responses_message_id ON raw_api_responses (message_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_raw_responses_conversation_id ON raw_api_responses (conversation_id)"
            )

            conn.commit()
            self.logger.info("SQLite database initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing SQLite database: {e}")
            raise PersistenceError(f"Failed to initialize SQLite database: {e}")
        finally:
            if conn:
                conn.close()

    def save_conversation(
        self,
        messages: List[Message],
        metadata: ConversationMetadata,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """
        Save a conversation to the SQLite database.

        Args:
            messages: List of messages in the conversation
            metadata: Metadata about the conversation
            filename: Optional name to identify the conversation (without extension)

        Returns:
            URI for the saved conversation or None on failure
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Generate a conversation ID if not provided
            conversation_id = str(metadata.session_id) if metadata.session_id else str(uuid.uuid4())

            # Generate a name for the conversation
            name = filename or f"conversation_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Convert metadata to JSON string (excluding fields stored separately)
            metadata_dict = metadata.__dict__.copy()
            for field in ["session_id", "saved_at", "persona_name", "model_name", "total_tokens"]:
                if field in metadata_dict:
                    metadata_dict.pop(field, None)

            metadata_json = json.dumps(metadata_dict)

            # Insert conversation - using ISO8601 datetime
            timestamp = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT OR REPLACE INTO conversations
                (id, name, model_name, persona_name, timestamp, saved_at, total_tokens, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    name,
                    metadata.model_name,
                    metadata.persona_name,
                    timestamp,
                    (
                        metadata.saved_at.isoformat()
                        if metadata.saved_at
                        else datetime.now().isoformat()
                    ),
                    metadata.total_tokens,
                    metadata_json,
                ),
            )

            # Get existing message IDs to avoid unique constraint errors
            cursor.execute("SELECT id FROM messages WHERE conversation_id = ?", (conversation_id,))
            existing_message_ids = {row[0] for row in cursor.fetchall()}

            # First, delete messages that are no longer in the conversation
            current_message_ids = {msg.id for msg in messages if msg.id}
            if current_message_ids:
                placeholders = ",".join(["?"] * len(current_message_ids))
                cursor.execute(
                    f"DELETE FROM messages WHERE conversation_id = ? AND id NOT IN ({placeholders})",
                    (conversation_id, *current_message_ids),
                )

            # Insert messages, using INSERT OR REPLACE to handle duplicates
            for position, msg in enumerate(messages):
                msg_id = msg.id or str(uuid.uuid4())
                tokens = (
                    msg.metadata.get("tokens_in", 0)
                    if msg.role == "user"
                    else msg.metadata.get("tokens_out", 0) if msg.role == "assistant" else 0
                )

                # Convert message metadata to JSON
                msg_metadata = msg.metadata or {}
                msg_metadata_json = json.dumps(msg_metadata)

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO messages
                    (id, conversation_id, role, content, timestamp, tokens, execution_count, cell_id, position, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        msg_id,
                        conversation_id,
                        msg.role,
                        msg.content,
                        timestamp,  # Using same timestamp as conversation for consistency
                        tokens,
                        msg.execution_count,
                        msg.cell_id,
                        position,
                        msg_metadata_json,
                    ),
                )

                # Only add debug log entry for new messages
                if msg_id not in existing_message_ids:
                    log_id = str(uuid.uuid4())
                    cursor.execute(
                        """
                        INSERT INTO debug_logs
                        (id, conversation_id, message_id, timestamp, log_level, component, event, details)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            log_id,
                            conversation_id,
                            msg_id,
                            timestamp,  # Using same timestamp as conversation
                            "INFO",
                            "SQLiteStore",
                            "message_saved",
                            json.dumps(
                                {
                                    "role": msg.role,
                                    "content_length": len(msg.content),
                                    "tokens": tokens,
                                    "position": position,
                                }
                            ),
                        ),
                    )

            conn.commit()

            # Return a URI that can be used to refer to this conversation
            uri = f"sqlite://{conversation_id}"
            self.logger.info(f"Saved conversation with {len(messages)} messages to SQLite: {uri}")
            return uri

        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Error saving conversation to SQLite: {e}")
            raise PersistenceError(f"Failed to save conversation to SQLite: {e}")
        finally:
            if conn:
                conn.close()

    def load_conversation(self, filepath: str) -> Tuple[List[Message], ConversationMetadata]:
        """
        Load a conversation from the SQLite database.

        Args:
            filepath: URI or ID of the conversation to load (e.g., "sqlite://conversation_id")

        Returns:
            Tuple of (messages, metadata)
        """
        conn = None
        try:
            # Extract conversation ID from the URI
            conversation_id = filepath
            if filepath.startswith("sqlite://"):
                conversation_id = filepath[len("sqlite://") :]

            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Access results by column name
            cursor = conn.cursor()

            # Get conversation metadata
            cursor.execute(
                """
                SELECT * FROM conversations WHERE id = ?
                """,
                (conversation_id,),
            )

            conversation = cursor.fetchone()
            if not conversation:
                self.logger.warning(f"Conversation not found: {filepath}")
                # Provide required arguments for ConversationMetadata (session_id as empty string)
                return [], ConversationMetadata(
                    session_id="",
                    saved_at=datetime.now(),
                    persona_name=None,
                    model_name=None,
                    total_tokens=0,
                )

            # Load additional metadata from JSON
            metadata_dict = json.loads(conversation["metadata"]) if conversation["metadata"] else {}

            # Ensure saved_at is always a datetime
            saved_at_val = conversation["saved_at"]
            if saved_at_val:
                try:
                    saved_at_dt = datetime.fromisoformat(saved_at_val)
                except Exception:
                    saved_at_dt = datetime.now()
            else:
                saved_at_dt = datetime.now()

            # Create metadata object
            metadata = ConversationMetadata(
                session_id=conversation["id"],
                saved_at=saved_at_dt,
                persona_name=conversation["persona_name"],
                model_name=conversation["model_name"],
                total_tokens=conversation["total_tokens"],
                **metadata_dict,
            )

            # Get messages for this conversation
            cursor.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY position ASC
                """,
                (conversation_id,),
            )

            messages = []
            for row in cursor.fetchall():
                # Parse message metadata
                msg_metadata = json.loads(row["metadata"]) if row["metadata"] else {}

                # Create message object with preserved message ID from the database
                # This is critical to ensure that when this message is saved again,
                # it will update the existing record rather than create a duplicate
                message = Message(
                    id=row["id"],  # Preserve original ID from database
                    role=row["role"],
                    content=row["content"],
                    execution_count=row["execution_count"],
                    cell_id=row["cell_id"],
                    metadata=msg_metadata,
                )

                messages.append(message)

            # Log debug information
            log_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO debug_logs
                (id, conversation_id, timestamp, log_level, component, event, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    conversation_id,
                    datetime.now().isoformat(),
                    "INFO",
                    "SQLiteStore",
                    "conversation_loaded",
                    json.dumps({"message_count": len(messages)}),
                ),
            )

            conn.commit()

            self.logger.info(f"Loaded conversation {conversation_id} with {len(messages)} messages")
            return messages, metadata

        except Exception as e:
            self.logger.error(f"Error loading conversation from SQLite: {e}")
            raise PersistenceError(f"Failed to load conversation from SQLite: {e}")
        finally:
            if conn:
                conn.close()

    def list_saved_conversations(self) -> List[Dict[str, Any]]:
        """
        List available saved conversations.

        Returns:
            List of conversation metadata dicts with paths
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Access results by column name
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT c.*,
                       COUNT(m.id) as message_count,
                       GROUP_CONCAT(t.tag, ',') as tags
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                LEFT JOIN tags t ON c.id = t.conversation_id
                GROUP BY c.id
                ORDER BY c.timestamp DESC
                """
            )

            conversations = []
            for row in cursor.fetchall():
                # Convert SQLite row to dictionary
                conv = dict(row)

                # Add path in the expected URI format
                conv["path"] = f"sqlite://{conv['id']}"

                # Split tags into a list if present
                if conv["tags"]:
                    conv["tags"] = conv["tags"].split(",")
                else:
                    conv["tags"] = []

                # Parse any additional metadata
                if conv["metadata"]:
                    additional_metadata = json.loads(conv["metadata"])
                    conv.update(additional_metadata)

                conversations.append(conv)

            self.logger.info(f"Listed {len(conversations)} saved conversations")
            return conversations

        except Exception as e:
            self.logger.error(f"Error listing conversations from SQLite: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation from the database.

        Args:
            conversation_id: ID of the conversation to delete

        Returns:
            True if successful, False otherwise
        """
        conn = None
        try:
            # Extract conversation ID from the URI if needed
            if conversation_id.startswith("sqlite://"):
                conversation_id = conversation_id[len("sqlite://") :]

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Delete messages first (due to foreign key constraint)
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))

            # Delete tags
            cursor.execute("DELETE FROM tags WHERE conversation_id = ?", (conversation_id,))

            # Delete debug logs
            cursor.execute("DELETE FROM debug_logs WHERE conversation_id = ?", (conversation_id,))

            # Delete conversation
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

            row_count = cursor.rowcount
            conn.commit()

            success = row_count > 0
            if success:
                self.logger.info(f"Deleted conversation {conversation_id}")
            else:
                self.logger.warning(f"No conversation found to delete with ID {conversation_id}")

            return success

        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Error deleting conversation from SQLite: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def add_tag(self, conversation_id: str, tag: str) -> bool:
        """
        Add a tag to a conversation for easier filtering.

        Args:
            conversation_id: ID of the conversation to tag
            tag: The tag to add

        Returns:
            True if successful, False otherwise
        """
        conn = None
        try:
            # Extract conversation ID from the URI if needed
            if conversation_id.startswith("sqlite://"):
                conversation_id = conversation_id[len("sqlite://") :]

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Add tag (the UNIQUE constraint will prevent duplicates)
            cursor.execute(
                "INSERT OR IGNORE INTO tags (conversation_id, tag) VALUES (?, ?)",
                (conversation_id, tag),
            )

            conn.commit()
            self.logger.info(f"Added tag '{tag}' to conversation {conversation_id}")
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Error adding tag to conversation: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def remove_tag(self, conversation_id: str, tag: str) -> bool:
        """
        Remove a tag from a conversation.

        Args:
            conversation_id: ID of the conversation
            tag: The tag to remove

        Returns:
            True if successful, False otherwise
        """
        conn = None
        try:
            # Extract conversation ID from the URI if needed
            if conversation_id.startswith("sqlite://"):
                conversation_id = conversation_id[len("sqlite://") :]

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Remove tag
            cursor.execute(
                "DELETE FROM tags WHERE conversation_id = ? AND tag = ?", (conversation_id, tag)
            )

            conn.commit()
            self.logger.info(f"Removed tag '{tag}' from conversation {conversation_id}")
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Error removing tag from conversation: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def search_conversations(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for conversations by content.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of matching conversation metadata
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # SQLite FTS would be better but for simplicity we'll use LIKE
            cursor.execute(
                """
                SELECT DISTINCT c.*,
                       COUNT(DISTINCT m.id) as message_count
                FROM conversations c
                JOIN messages m ON c.id = m.conversation_id
                WHERE m.content LIKE ?
                   OR c.name LIKE ?
                   OR c.persona_name LIKE ?
                GROUP BY c.id
                ORDER BY c.timestamp DESC
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            )

            conversations = []
            for row in cursor.fetchall():
                # Convert SQLite row to dictionary
                conv = dict(row)

                # Add path in the expected URI format
                conv["path"] = f"sqlite://{conv['id']}"

                # Get tags for this conversation
                cursor.execute("SELECT tag FROM tags WHERE conversation_id = ?", (conv["id"],))
                conv["tags"] = [row["tag"] for row in cursor.fetchall()]

                # Parse any additional metadata
                if conv["metadata"]:
                    additional_metadata = json.loads(conv["metadata"])
                    conv.update(additional_metadata)

                conversations.append(conv)

            self.logger.info(f"Found {len(conversations)} conversations matching '{query}'")
            return conversations

        except Exception as e:
            self.logger.error(f"Error searching conversations: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored conversations.

        Returns:
            Dictionary with statistics
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            stats = {}

            # Count conversations
            cursor.execute("SELECT COUNT(*) FROM conversations")
            stats["total_conversations"] = cursor.fetchone()[0]

            # Count messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            stats["total_messages"] = cursor.fetchone()[0]

            # Count by role
            cursor.execute("SELECT role, COUNT(*) FROM messages GROUP BY role")
            stats["messages_by_role"] = {role: count for role, count in cursor.fetchall()}

            # Sum tokens
            cursor.execute("SELECT SUM(tokens) FROM messages")
            stats["total_tokens"] = cursor.fetchone()[0] or 0

            # Most active day
            cursor.execute(
                """
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM messages
                GROUP BY date
                ORDER BY count DESC
                LIMIT 1
                """
            )
            result = cursor.fetchone()
            if result:
                stats["most_active_day"] = {"date": result[0], "message_count": result[1]}

            # Most used model
            cursor.execute(
                """
                SELECT model_name, COUNT(*) as count
                FROM conversations
                WHERE model_name IS NOT NULL
                GROUP BY model_name
                ORDER BY count DESC
                LIMIT 1
                """
            )
            result = cursor.fetchone()
            if result and result[0]:
                stats["most_used_model"] = {"model": result[0], "count": result[1]}

            # Average tokens per message
            cursor.execute(
                """
                SELECT AVG(tokens) FROM messages WHERE tokens > 0
                """
            )
            stats["avg_tokens_per_message"] = cursor.fetchone()[0] or 0

            return stats

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
        finally:
            if conn:
                conn.close()

    def log_debug(
        self, conversation_id: str, component: str, event: str, details: Dict[str, Any]
    ) -> None:
        """
        Add a debug log entry for a conversation.

        Args:
            conversation_id: Related conversation ID
            component: Component generating the log
            event: Event type
            details: Event details
        """
        conn = None
        try:
            # Extract conversation ID from the URI if needed
            if conversation_id and conversation_id.startswith("sqlite://"):
                conversation_id = conversation_id[len("sqlite://") :]

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            log_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            details_json = json.dumps(details)

            cursor.execute(
                """
                INSERT INTO debug_logs
                (id, conversation_id, timestamp, log_level, component, event, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (log_id, conversation_id, timestamp, "DEBUG", component, event, details_json),
            )

            conn.commit()

        except Exception as e:
            self.logger.error(f"Error logging debug information: {e}")
        finally:
            if conn:
                conn.close()

    def store_raw_api_response(
        self,
        message_id: str,
        conversation_id: str,
        endpoint: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        response_time_ms: int,
        status_code: int = 200,
    ) -> Optional[str]:
        """
        Store a raw API response associated with a message.

        Args:
            message_id: ID of the related message
            conversation_id: ID of the related conversation
            endpoint: The API endpoint used
            request_data: The request payload
            response_data: The raw response from the API
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code

        Returns:
            ID of the stored raw response or None on failure
        """
        conn = None
        try:
            # Extract conversation ID from the URI if needed
            if conversation_id and conversation_id.startswith("sqlite://"):
                conversation_id = conversation_id[len("sqlite://") :]

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Generate a unique ID
            response_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()

            # Convert dictionaries to JSON
            request_json = json.dumps(request_data)
            response_json = json.dumps(response_data)

            cursor.execute(
                """
                INSERT INTO raw_api_responses
                (id, message_id, conversation_id, timestamp, endpoint,
                request_data, response_data, response_time_ms, status_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    response_id,
                    message_id,
                    conversation_id,
                    timestamp,
                    endpoint,
                    request_json,
                    response_json,
                    response_time_ms,
                    status_code,
                ),
            )

            conn.commit()
            self.logger.info(f"Stored raw API response for message {message_id}")
            return response_id

        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Error storing raw API response: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_raw_api_responses(
        self, message_id: Optional[str] = None, conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get raw API responses for a message or conversation.

        Args:
            message_id: Optional message ID filter
            conversation_id: Optional conversation ID filter

        Returns:
            List of raw API responses
        """
        conn = None
        try:
            # Extract conversation ID from the URI if needed
            if conversation_id and conversation_id.startswith("sqlite://"):
                conversation_id = conversation_id[len("sqlite://") :]

            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Build query based on provided filters
            query = "SELECT * FROM raw_api_responses WHERE 1=1"
            params = []

            if message_id:
                query += " AND message_id = ?"
                params.append(message_id)

            if conversation_id:
                query += " AND conversation_id = ?"
                params.append(conversation_id)

            query += " ORDER BY timestamp DESC"

            cursor.execute(query, params)

            responses = []
            for row in cursor.fetchall():
                # Convert SQLite row to dictionary
                response = dict(row)

                # Parse JSON data
                if response["request_data"]:
                    response["request_data"] = json.loads(response["request_data"])

                if response["response_data"]:
                    response["response_data"] = json.loads(response["response_data"])

                responses.append(response)

            return responses

        except Exception as e:
            self.logger.error(f"Error retrieving raw API responses: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_message_with_raw_response(self, message_id: str) -> Dict[str, Any]:
        """
        Get a message with its associated raw API response.

        Args:
            message_id: ID of the message

        Returns:
            Dictionary containing message and raw response data
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get message
            cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
            message_row = cursor.fetchone()

            if not message_row:
                return {"error": f"Message {message_id} not found"}

            message = dict(message_row)

            # Parse message metadata
            if message["metadata"]:
                message["metadata"] = json.loads(message["metadata"])

            # Get raw API responses for this message
            cursor.execute(
                "SELECT * FROM raw_api_responses WHERE message_id = ? ORDER BY timestamp DESC",
                (message_id,),
            )

            raw_responses = []
            for row in cursor.fetchall():
                response = dict(row)

                # Parse JSON data
                if response["request_data"]:
                    response["request_data"] = json.loads(response["request_data"])

                if response["response_data"]:
                    response["response_data"] = json.loads(response["response_data"])

                raw_responses.append(response)

            result = {"message": message, "raw_responses": raw_responses}

            return result

        except Exception as e:
            self.logger.error(f"Error getting message with raw response: {e}")
            return {"error": str(e)}
        finally:
            if conn:
                conn.close()
