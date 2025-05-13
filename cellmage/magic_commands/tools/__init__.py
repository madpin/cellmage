"""
Magic command modules for CellMage (tools).

This package contains magic commands for integrations and tools.
"""

from .confluence_magic import ConfluenceMagics
from .gdocs_magic import GoogleDocsMagic
from .github_magic import GitHubMagics
from .gitlab_magic import GitLabMagics
from .image_magic import ImageMagics
from .jira_magic import JiraMagics
from .webcontent_magic import WebContentMagics

__all__ = [
    "ConfluenceMagics",
    "GoogleDocsMagic",
    "GitHubMagics",
    "GitLabMagics",
    "ImageMagics",
    "JiraMagics",
    "WebContentMagics",
]
