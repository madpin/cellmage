import os
import logging
import yaml
from typing import Dict, List, Optional, Any

from ..models import PersonaConfig
from ..interfaces import PersonaLoader, SnippetProvider
from ..exceptions import ResourceNotFoundError


class FileLoader(PersonaLoader, SnippetProvider):
    """
    Loads personas and snippets from markdown files.
    
    Implements both PersonaLoader and SnippetProvider interfaces.
    """
    
    def __init__(self, personas_dir: str = "llm_personas", snippets_dir: str = "snippets"):
        """
        Initialize the file loader.
        
        Args:
            personas_dir: Directory containing persona markdown files
            snippets_dir: Directory containing snippet markdown files
        """
        self.personas_dir = personas_dir
        self.snippets_dir = snippets_dir
        self.logger = logging.getLogger(__name__)
        
        # Ensure directories exist
        for directory in [self.personas_dir, self.snippets_dir]:
            try:
                os.makedirs(directory, exist_ok=True)
                self.logger.info(f"Directory setup: {os.path.abspath(directory)}")
            except OSError as e:
                self.logger.error(f"Error creating directory '{directory}': {e}")

    def list_personas(self) -> List[str]:
        """
        List available personas.
        
        Returns:
            List of persona names (without .md extension)
        """
        try:
            if not os.path.isdir(self.personas_dir):
                self.logger.warning(f"Personas directory not found: {os.path.abspath(self.personas_dir)}")
                return []
                
            personas = []
            for filename in os.listdir(self.personas_dir):
                if filename.lower().endswith(".md"):
                    name = os.path.splitext(filename)[0]
                    personas.append(name)
            return sorted(personas)
        except Exception as e:
            self.logger.error(f"Error listing personas: {e}")
            return []
            
    def get_persona(self, name: str) -> Optional[PersonaConfig]:
        """
        Load a persona configuration from a markdown file.
        
        Args:
            name: Name of the persona (without .md extension)
            
        Returns:
            PersonaConfig object or None if not found
        """
        # Case insensitive matching
        name_lower = name.lower()
        
        # First try exact filename match
        filepath = os.path.join(self.personas_dir, f"{name}.md")
        if os.path.isfile(filepath):
            return self._load_persona_file(filepath, name)
            
        # Otherwise try case-insensitive match
        try:
            if not os.path.isdir(self.personas_dir):
                self.logger.warning(f"Personas directory not found: {os.path.abspath(self.personas_dir)}")
                return None
                
            for filename in os.listdir(self.personas_dir):
                if filename.lower().endswith(".md"):
                    file_name_base = os.path.splitext(filename)[0]
                    if file_name_base.lower() == name_lower:
                        filepath = os.path.join(self.personas_dir, filename)
                        return self._load_persona_file(filepath, file_name_base)
                        
            self.logger.warning(f"Persona '{name}' not found in {self.personas_dir}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting persona '{name}': {e}")
            return None
            
    def _load_persona_file(self, filepath: str, original_name: str) -> Optional[PersonaConfig]:
        """
        Parse a markdown file into a PersonaConfig object.
        
        Args:
            filepath: Path to the markdown file
            original_name: Original name of the persona
            
        Returns:
            PersonaConfig object or None if parsing fails
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Manual YAML frontmatter parsing
            config = {}
            system_message = ""
            
            if content.startswith("---"):
                # Find the closing --- marker
                parts = content[3:].split("---", 1)
                if len(parts) >= 2:
                    yaml_part = parts[0].strip()
                    try:
                        config = yaml.safe_load(yaml_part) or {}
                        system_message = parts[1].strip()
                    except Exception as yaml_err:
                        self.logger.error(f"Error parsing YAML frontmatter: {yaml_err}")
                        system_message = content.strip()
                else:
                    # No closing --- found, treat whole content as system message
                    system_message = content.strip()
            else:
                # No frontmatter, treat whole content as system message
                system_message = content.strip()
                
            abs_filepath = os.path.abspath(filepath)
            self.logger.debug(f"Loaded persona '{original_name}' from {abs_filepath}")
            
            return PersonaConfig(
                system_message=system_message,
                config=config,
                source_file=abs_filepath,
                original_name=original_name
            )
        except Exception as e:
            self.logger.error(f"Error loading persona file '{filepath}': {e}")
            return None
            
    def list_snippets(self) -> List[str]:
        """
        List available snippets.
        
        Returns:
            List of snippet names (without .md extension)
        """
        try:
            if not os.path.isdir(self.snippets_dir):
                self.logger.warning(f"Snippets directory not found: {os.path.abspath(self.snippets_dir)}")
                return []
                
            snippets = []
            for filename in os.listdir(self.snippets_dir):
                if filename.lower().endswith(".md"):
                    name = os.path.splitext(filename)[0]
                    snippets.append(name)
            return sorted(snippets)
        except Exception as e:
            self.logger.error(f"Error listing snippets: {e}")
            return []
            
    def get_snippet(self, name: str) -> Optional[str]:
        """
        Load a snippet from a markdown file.
        
        Args:
            name: Name of the snippet (without .md extension)
            
        Returns:
            Snippet content as string or None if not found
        """
        # Add .md extension if not provided
        if not name.lower().endswith(".md"):
            name += ".md"
            
        filepath = os.path.join(self.snippets_dir, name)
        
        try:
            if not os.path.isfile(filepath):
                self.logger.warning(f"Snippet '{name}' not found at {filepath}")
                return None
                
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            self.logger.debug(f"Loaded snippet '{name}' from {filepath}")
            return content
        except Exception as e:
            self.logger.error(f"Error loading snippet '{name}': {e}")
            return None

