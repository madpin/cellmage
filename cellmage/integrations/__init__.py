"""
Integration modules for CellMage.

This package provides integrations with various third-party services and systems.
"""

from . import (
    base_magic,
    confluence_magic,
    gdocs_magic,
    github_magic,
    gitlab_magic,
    jira_magic,
    sqlite_magic,
    webcontent_magic,
)

__all__ = [
    "base_magic",
    "confluence_magic",
    "gdocs_magic",
    "github_magic",
    "gitlab_magic",
    "jira_magic",
    "sqlite_magic",
    "webcontent_magic",
]
