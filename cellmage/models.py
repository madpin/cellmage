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
    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )  # Store information like model, tokens, etc.

    def to_llm_format(self) -> Dict[str, str]:
        """Converts message to the format expected by LLM clients (e.g., OpenAI)."""
        # Basic format, might need adjustment based on specific LLM client needs
        return {"role": self.role, "content": self.content}


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
