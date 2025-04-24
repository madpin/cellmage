import uuid
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class Message(BaseModel):
    """Represents a single message in the conversation history."""
    role: Literal['system', 'user', 'assistant']
    content: str
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    execution_count: Optional[int] = None # Environment-specific metadata
    cell_id: Optional[str] = None         # Environment-specific metadata
    metadata: Dict[str, Any] = Field(default_factory=dict) # For future extensibility

    def to_llm_format(self) -> Dict[str, str]:
        """Converts message to the format expected by LLM clients (e.g., OpenAI)."""
        # Basic format, might need adjustment based on specific LLM client needs
        return {"role": self.role, "content": self.content}

class PersonaConfig(BaseModel):
    """Configuration loaded from a personality resource."""
    name: str # Typically derived from the resource name/file name
    system_prompt: str
    llm_params: Dict[str, Any] = Field(default_factory=dict) # e.g., model, temperature
    source_path: Optional[str] = None # Path to the original file, if applicable

class ConversationMetadata(BaseModel):
    """Metadata saved with a conversation history."""
    session_id: str
    saved_at: datetime
    persona_name: Optional[str]
    initial_settings: Dict[str, Any] # Snapshot of relevant settings at save time
    message_count: int
    custom_tags: Dict[str, str] = Field(default_factory=dict)

