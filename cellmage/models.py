import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Message in a conversation."""

    role: str
    content: str
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    execution_count: Optional[int] = None  # Environment-specific metadata
    cell_id: Optional[str] = None  # Environment-specific metadata
    is_snippet: bool = False  # Whether this message was added from a snippet
    is_confluence: bool = False  # Whether this message was added from Confluence
    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )  # Store information like model, tokens, etc.

    def to_llm_format(self) -> Dict[str, str]:
        """Converts message to the format expected by LLM clients (e.g., OpenAI)."""
        # Basic format, might need adjustment based on specific LLM client needs
        return {"role": self.role, "content": self.content}

    @classmethod
    def generate_message_id(
        cls,
        role: str,
        content: str,
        cell_id: Optional[str] = None,
        execution_count: Optional[int] = None,
    ) -> str:
        """
        Generate a deterministic message ID that includes execution context information.
        This helps avoid duplicate IDs for different messages in the same cell.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            cell_id: Jupyter cell ID
            execution_count: Execution counter

        Returns:
            A message ID string that includes context and content information
        """
        import hashlib

        # Create a prefix with role
        prefix = f"{role[0].upper()}"  # U for user, A for assistant, S for system

        # Add execution context if available
        context_part = ""
        if cell_id:
            # Use just the first 8 chars of the cell ID
            short_cell_id = cell_id[:8] if len(cell_id) > 8 else cell_id
            context_part += f"-{short_cell_id}"
        if execution_count is not None:
            context_part += f"-{execution_count}"

        # Create a content hash to differentiate messages with the same role and cell
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]

        # Add a timestamp for absolute uniqueness (different executions of same content)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        # Combine all parts
        message_id = f"{prefix}{context_part}-{content_hash}-{timestamp}"

        return message_id


class PersonaConfig(BaseModel):
    """Configuration for an LLM persona."""

    name: str
    system_message: str
    config: Dict[str, Any] = Field(default_factory=dict)
    source_path: Optional[str] = None


class ConversationMetadata(BaseModel):
    """Metadata for a conversation."""

    session_id: str
    saved_at: datetime
    persona_name: Optional[str] = None
    model_name: Optional[str] = None
    total_tokens: Optional[int] = None
