from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union


@dataclass
class Message:
    """Represents a single message in a conversation."""
    
    role: str  # "system", "user", or "assistant"
    content: str
    id: str  # Unique message identifier
    execution_count: Optional[int] = None  # Cell execution count when created
    cell_id: Optional[str] = None  # Persistent cell identifier
    is_snippet: bool = False  # Whether this message was loaded from a snippet


@dataclass
class PersonaConfig:
    """Configuration for a persona/personality."""
    
    system_message: str  # System message defining the persona
    config: Dict[str, Any] = field(default_factory=dict)  # Additional config options
    source_file: Optional[str] = None  # Source file path
    original_name: Optional[str] = None  # Original name for display


@dataclass
class ConversationMetadata:
    """Metadata about a saved conversation."""
    
    saved_at: datetime = field(default_factory=datetime.now)  # When the conversation was saved
    total_messages: int = 0  # Total number of messages
    turns: int = 0  # Number of conversation turns
    default_model_name: Optional[str] = None  # Model used 
    default_personality_name: Optional[str] = None  # Personality name used
    personality_config: Optional[Dict[str, Any]] = None  # Personality config if used
    execution_counts: List[int] = field(default_factory=list)  # List of execution counts
    cell_ids_present: int = 0  # Number of cell IDs in the conversation

