import logging
import os
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    import yaml
else:
    import yaml  # type: ignore

from ..exceptions import PersistenceError
from ..interfaces import HistoryStore
from ..models import ConversationMetadata, Message


class MarkdownStore(HistoryStore):
    """
    Stores conversation history as markdown files with YAML frontmatter.
    """

    def __init__(self, save_dir: str = "llm_conversations"):
        """
        Initialize the markdown store.

        Args:
            save_dir: Directory to save conversations
        """
        self.save_dir = save_dir
        self.logger = logging.getLogger(__name__)

        # Ensure save directory exists
        if self.save_dir:
            try:
                os.makedirs(self.save_dir, exist_ok=True)
                self.logger.info(f"Save directory setup: {os.path.abspath(self.save_dir)}")
            except OSError as e:
                self.logger.error(f"Error creating save directory '{save_dir}': {e}")

    def save_conversation(
        self,
        messages: List[Message],
        metadata: ConversationMetadata,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """
        Save a conversation to a markdown file.

        Args:
            messages: List of messages in the conversation
            metadata: Metadata about the conversation
            filename: Optional filename (without extension) to use

        Returns:
            Path to the saved file or None on failure
        """
        if not self.save_dir:
            self.logger.error("Save failed: No save directory configured")
            return None

        if not messages:
            self.logger.warning("Save skipped: No messages to save")
            return None

        # Generate filename if not provided
        if not filename:
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            first_user_msg = next((m for m in messages if m.role == "user"), None)

            if first_user_msg:
                # Get first few words of first user message for filename
                first_words = "_".join(first_user_msg.content.split()[:5])
                safe_words = "".join(c if c.isalnum() or c in ["_"] else "" for c in first_words)
                filename = f"chat_{now}_{safe_words if safe_words else 'conversation'}"
            else:
                filename = f"chat_{now}"
        else:
            # Only add timestamp if the filename doesn't already contain a date pattern (YYYYMMDD_HHMMSS)
            if not any(part.isdigit() and len(part) == 8 for part in filename.split("_")):
                now = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{filename}_{now}"

        # Ensure filename doesn't have extension
        filename = os.path.splitext(filename)[0]
        full_path = os.path.join(self.save_dir, f"{filename}.md")

        # Calculate additional metadata that might be useful
        total_messages = len(messages)
        turns = len([m for m in messages if m.role == "user"])

        # Format the current date for display
        current_date = datetime.now().strftime("%B %d, %Y")

        # Convert metadata to serializable dict using only fields that exist
        metadata_dict = {
            "session_id": str(metadata.session_id),
            "saved_at": metadata.saved_at.isoformat(),
            "total_messages": total_messages,  # Calculated, not from ConversationMetadata
            "turns": turns,  # Calculated, not from ConversationMetadata
        }

        # Only add optional fields if they're present
        if metadata.persona_name:
            metadata_dict["persona_name"] = metadata.persona_name

        if metadata.model_name:
            metadata_dict["model_name"] = metadata.model_name

        if metadata.total_tokens:
            metadata_dict["total_tokens"] = metadata.total_tokens

        # Prepare content parts
        content_parts = []

        # Add date header
        content_parts.append(f"# Conversation on {current_date}\n\n")

        # Group messages by role for better readability
        current_role: Optional[str] = None
        current_text: List[str] = []

        for msg in messages:
            if msg.role != current_role:
                # Save previous role's content if we have any
                if current_text:
                    role_prefix = (
                        "**You:**"
                        if current_role == "user"
                        else f"**{current_role or 'Unknown'}:**"
                    )
                    content_parts.append(f"{role_prefix}\n{''.join(current_text)}\n")
                    current_text = []

                # Only add separator after non-user roles
                if current_role and current_role != "user":
                    content_parts.append("---\n")

                current_role = msg.role

            current_text.append(f"{msg.content}\n")

        # Add any remaining text
        if current_text:
            role_prefix = (
                "**You:**" if current_role == "user" else f"**{current_role or 'Unknown'}:**"
            )
            content_parts.append(f"{role_prefix}\n{''.join(current_text)}\n")

        # Add separator after final assistant/system message
        if current_role and current_role != "user":
            content_parts.append("---\n")

        content = "".join(content_parts)

        try:
            # Write the file with YAML frontmatter and content
            with open(full_path, "w", encoding="utf-8") as f:
                f.write("---\n")
                yaml.dump(metadata_dict, f, default_flow_style=False)
                f.write("---\n\n")
                f.write(content.strip())

            self.logger.info(f"Conversation saved to {os.path.abspath(full_path)}")
            return full_path
        except Exception as e:
            self.logger.error(f"Error saving conversation to {full_path}: {e}")
            raise PersistenceError(f"Failed to save conversation: {e}")

    def load_conversation(self, filepath: str) -> Tuple[List[Message], ConversationMetadata]:
        """
        Load a conversation from a markdown file.

        Args:
            filepath: Path to the conversation file

        Returns:
            Tuple of (messages, metadata)
        """
        if not os.path.isfile(filepath):
            self.logger.error(f"File not found: {filepath}")
            raise PersistenceError(f"Conversation file not found: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse frontmatter and content
            if not content.startswith("---"):
                self.logger.error(f"Invalid conversation file format: {filepath}")
                raise PersistenceError(
                    f"Invalid conversation file format, missing frontmatter: {filepath}"
                )

            # Split on the second occurrence of '---'
            parts = content[3:].split("---", 1)
            if len(parts) < 2:
                self.logger.error(f"Invalid conversation file format: {filepath}")
                raise PersistenceError(
                    f"Invalid conversation file format, incomplete frontmatter: {filepath}"
                )

            # Parse frontmatter
            yaml_part = parts[0].strip()
            metadata_dict = yaml.safe_load(yaml_part) or {}

            # Create metadata object - Fix: Keep session_id as a string instead of converting to UUID
            metadata = ConversationMetadata(
                session_id=metadata_dict.get("session_id", str(uuid.uuid4())),  # Keep as string
                saved_at=datetime.fromisoformat(
                    metadata_dict.get("saved_at", datetime.now().isoformat())
                ),
                persona_name=metadata_dict.get("persona_name"),
                model_name=metadata_dict.get("model_name"),
                total_tokens=metadata_dict.get("total_tokens"),
            )

            # Parse content into messages
            messages = []
            content_text = parts[1].strip()

            # Simple parsing based on role markers
            # More robust parsing might be needed for complex conversations
            current_role: Optional[str] = None
            current_content: List[str] = []

            for line in content_text.split("\n"):
                if line.startswith("**System:**"):
                    if current_role and current_content:
                        messages.append(
                            Message(
                                role=current_role,
                                content="\n".join(current_content).strip(),
                                id=str(uuid.uuid4()),
                            )
                        )
                        current_content = []
                    current_role = "system"
                elif line.startswith("**You:**"):
                    if current_role and current_content:
                        messages.append(
                            Message(
                                role=current_role,
                                content="\n".join(current_content).strip(),
                                id=str(uuid.uuid4()),
                            )
                        )
                        current_content = []
                    current_role = "user"
                elif line.startswith("**Assistant:**"):
                    if current_role and current_content:
                        messages.append(
                            Message(
                                role=current_role,
                                content="\n".join(current_content).strip(),
                                id=str(uuid.uuid4()),
                            )
                        )
                        current_content = []
                    current_role = "assistant"
                elif line == "---":
                    # Skip separator lines
                    continue
                else:
                    # Add line to current content if we have a role
                    if current_role:
                        current_content.append(line)

            # Add the final message
            if current_role and current_content:
                messages.append(
                    Message(
                        role=current_role,
                        content="\n".join(current_content).strip(),
                        id=str(uuid.uuid4()),
                    )
                )

            self.logger.info(f"Loaded conversation from {filepath} with {len(messages)} messages")
            return messages, metadata

        except Exception as e:
            self.logger.error(f"Error loading conversation from {filepath}: {e}")
            raise PersistenceError(f"Failed to load conversation: {e}")

    def list_saved_conversations(self) -> List[Dict[str, Any]]:
        """
        List available saved conversations.

        Returns:
            List of conversation metadata dicts with paths
        """
        if not self.save_dir or not os.path.isdir(self.save_dir):
            self.logger.warning(f"Save directory not found: {self.save_dir}")
            return []

        conversations = []

        try:
            for filename in os.listdir(self.save_dir):
                if filename.lower().endswith(".md"):
                    filepath = os.path.join(self.save_dir, filename)
                    try:
                        # Open the file and read just the frontmatter
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()

                        if content.startswith("---"):
                            parts = content[3:].split("---", 1)
                            if len(parts) >= 1:
                                yaml_part = parts[0].strip()
                                metadata = yaml.safe_load(yaml_part) or {}
                                metadata["filepath"] = filepath
                                metadata["filename"] = filename
                                conversations.append(metadata)
                    except Exception as e:
                        self.logger.error(f"Error reading metadata from {filepath}: {e}")

            self.logger.info(f"Found {len(conversations)} saved conversations")
            return conversations
        except Exception as e:
            self.logger.error(f"Error listing conversations in {self.save_dir}: {e}")
            return []
