import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging
from datetime import datetime

from ..interfaces import HistoryStore
from ..models import Message, ConversationMetadata
from ..exceptions import PersistenceError, ResourceNotFoundError

logger = logging.getLogger(__name__)

# Use the same parser as FileLoader for consistency
from ..resources.file_loader import _parse_markdown_frontmatter, YAML_FRONT_MATTER_REGEX

class MarkdownStore(HistoryStore):
    """Saves and loads conversation history to/from Markdown files with YAML frontmatter."""

    DEFAULT_EXTENSION = ".md"

    def __init__(self, base_dir: Path):
        """
        Initializes the MarkdownStore.

        Args:
            base_dir: The directory where conversation files will be stored.
        """
        self.base_dir = Path(base_dir)
        if not self.base_dir.is_dir():
            logger.warning(f"History storage directory not found: {self.base_dir}. Creating it.")
            self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"MarkdownStore initialized. Storage directory: '{self.base_dir}'")

    def _get_path(self, identifier: str) -> Path:
        """Constructs the full path for a given identifier."""
        # Ensure identifier doesn't contain path traversal characters for security
        safe_identifier = Path(identifier).name
        if not safe_identifier.endswith(self.DEFAULT_EXTENSION):
             safe_identifier += self.DEFAULT_EXTENSION
        return self.base_dir / safe_identifier

    def save(self, messages: List[Message], metadata: ConversationMetadata) -> str:
        """
        Saves the history and metadata to a markdown file.
        Metadata is stored as YAML frontmatter.
        Messages are appended, formatted as markdown blockquotes or similar.
        """
        identifier = metadata.session_id # Use session ID from metadata as filename base
        file_path = self._get_path(identifier)
        logger.debug(f"Attempting to save session '{identifier}' to {file_path}")

        try:
            # Prepare frontmatter (serialize metadata)
            # Exclude session_id as it's used for the filename
            metadata_dict = metadata.model_dump(exclude={'session_id'}, mode='json') # Use 'json' mode for datetime serialization
            frontmatter_yaml = yaml.dump(metadata_dict, default_flow_style=False, sort_keys=False)

            # Prepare message content
            message_content = "\n\n".join(self._format_message_as_markdown(msg) for msg in messages)

            # Combine and write
            full_content = f"---\n{frontmatter_yaml}---\n\n{message_content}\n"

            file_path.write_text(full_content, encoding='utf-8')
            logger.info(f"Successfully saved session '{identifier}' to {file_path}")
            return str(file_path) # Return the actual path saved

        except yaml.YAMLError as e:
             logger.exception(f"Failed to serialize metadata to YAML for session '{identifier}'.")
             raise PersistenceError(f"YAML serialization error saving '{identifier}': {e}") from e
        except IOError as e:
             logger.exception(f"Failed to write history file: {file_path}")
             raise PersistenceError(f"File write error saving '{identifier}': {e}") from e
        except Exception as e:
             logger.exception(f"An unexpected error occurred while saving session '{identifier}'.")
             raise PersistenceError(f"Unexpected error saving '{identifier}': {e}") from e

    def load(self, identifier: str) -> Tuple[List[Message], ConversationMetadata]:
        """
        Loads history and metadata from a markdown file.
        """
        file_path = self._get_path(identifier)
        logger.debug(f"Attempting to load session '{identifier}' from {file_path}")

        if not file_path.is_file():
            raise ResourceNotFoundError("history", identifier)

        try:
            full_content = file_path.read_text(encoding='utf-8')

            # Parse frontmatter and main content
            frontmatter_dict, message_section = _parse_markdown_frontmatter(full_content)

            # --- TODO: Implement robust parsing of message_section back into Message objects ---
            # This is the complex part. How were messages formatted in _format_message_as_markdown?
            # Need a corresponding parser here.
            # Placeholder: Assume simple parsing for now.
            messages = self._parse_messages_from_markdown(message_section)
            # --- End Placeholder ---

            # Validate and deserialize metadata
            # Add back session_id from the identifier used
            frontmatter_dict['session_id'] = Path(identifier).stem # Use stem to remove suffix if present
            metadata = ConversationMetadata.model_validate(frontmatter_dict)

            logger.info(f"Successfully loaded session '{identifier}' from {file_path}. Found {len(messages)} messages.")
            return messages, metadata

        except FileNotFoundError: # Defensive
             raise ResourceNotFoundError("history", identifier) from None
        except yaml.YAMLError as e:
             logger.exception(f"Failed to parse YAML frontmatter from file: {file_path}")
             raise PersistenceError(f"YAML parsing error loading '{identifier}': {e}") from e
        except Exception as e: # Catches Pydantic validation errors too
            logger.exception(f"Failed to load or parse history file: {file_path}")
            raise PersistenceError(f"Error loading history '{identifier}': {e}") from e

    def list_saved(self) -> List[str]:
        """Lists identifiers (filenames without extension) of saved histories."""
        if not self.base_dir.exists():
             logger.warning(f"Cannot list saved histories, directory does not exist: {self.base_dir}")
             return []
        try:
            # Return the stem (filename without suffix)
            return sorted([p.stem for p in self.base_dir.glob(f"*{self.DEFAULT_EXTENSION}") if p.is_file()])
        except Exception as e:
             logger.exception(f"Failed to list files in history directory: {self.base_dir}")
             return []

    def _format_message_as_markdown(self, message: Message) -> str:
        """Formats a single Message object into a markdown string for saving."""
        # Example format: Role as heading, metadata as details, content as blockquote
        # --- TODO: Finalize a robust and parsable format ---
        metadata_str = f"ID: {message.id} | Timestamp: {message.timestamp.isoformat()} | Cell: {message.cell_id or 'N/A'} | Exec: {message.execution_count or 'N/A'}"
        if message.metadata:
             metadata_str += f" | Meta: {message.metadata}"

        return f"### {message.role.capitalize()}\n`{metadata_str}`\n\n> {message.content.strip()}" # Simple blockquote example

    def _parse_messages_from_markdown(self, markdown_content: str) -> List[Message]:
        """Parses the message section of the markdown file back into Message objects."""
        # --- TODO: Implement the parser corresponding to _format_message_as_markdown ---
        # This needs to reliably split the content back into individual messages
        # and extract role, content, and potentially reconstruct metadata.
        # This is non-trivial if the content itself contains markdown similar to the separators.
        # Using separators like '---' between messages might be more robust.
        logger.warning("_parse_messages_from_markdown is not fully implemented. Returning empty list.")
        messages: List[Message] = []
        # Placeholder logic: Split by headings? Very fragile.
        # parts = re.split(r'\n### (System|User|Assistant)\n', markdown_content)
        # ... complex parsing logic needed ...
        return messages

