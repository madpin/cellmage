"""
Confluence API integration utilities for Cellmage.

This module provides functions for interacting with the Confluence API.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from atlassian import Confluence
from bs4 import BeautifulSoup

# Check if html2text is available for Markdown conversion
try:
    import html2text

    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Class for interacting with the Confluence API."""

    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize the Confluence client.

        Args:
            url: Confluence URL
            username: Username/email for authentication
            password: API token or password
        """
        # Try to get credentials from environment variables if not provided
        self.url = url or os.environ.get("CONFLUENCE_URL") or os.environ.get("JIRA_URL")
        self.username = username or os.environ.get("JIRA_USER_EMAIL")
        self.password = password or os.environ.get("JIRA_API_TOKEN")

        if not self.url:
            raise ValueError(
                "Confluence URL not provided. Set CONFLUENCE_URL or JIRA_URL environment variable."
            )
        if not self.username:
            raise ValueError("Username not provided. Set JIRA_USER_EMAIL environment variable.")
        if not self.password:
            raise ValueError("API token not provided. Set JIRA_API_TOKEN environment variable.")

        # Create Confluence client
        self.client = Confluence(
            url=self.url,
            username=self.username,
            password=self.password,
            cloud=True,  # Assume Confluence Cloud by default
        )

    def get_page_by_id(self, page_id: str) -> Dict[str, Any]:
        """
        Get a Confluence page by its ID.

        Args:
            page_id: The ID of the page to retrieve

        Returns:
            Dict containing page information
        """
        try:
            page = self.client.get_page_by_id(page_id, expand="body.storage")
            return page
        except Exception as e:
            logger.error(f"Error fetching Confluence page with ID {page_id}: {e}")
            raise

    def get_page_by_title(self, space_key: str, title: str) -> Dict[str, Any]:
        """
        Get a Confluence page by its space key and title.

        Args:
            space_key: The space key
            title: The title of the page

        Returns:
            Dict containing page information
        """
        try:
            page = self.client.get_page_by_title(space_key, title, expand="body.storage")
            return page
        except Exception as e:
            logger.error(f"Error fetching Confluence page '{title}' in space '{space_key}': {e}")
            raise

    def search_pages(self, cql: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search Confluence using CQL (Confluence Query Language).

        Args:
            cql: The CQL query string
            limit: Maximum number of results to return

        Returns:
            List of dicts containing page information
        """
        try:
            results = self.client.cql(cql, limit=limit, expand="body.storage")
            return results.get("results", [])
        except Exception as e:
            logger.error(f"Error searching Confluence with CQL '{cql}': {e}")
            raise


def parse_page_identifier(identifier: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a page identifier in the format SPACE:Title or ID.

    Args:
        identifier: Page identifier

    Returns:
        Tuple of (space_key, title) or (None, ID) if an ID is provided
    """
    # Strip quotes if present
    identifier = identifier.strip()
    if (identifier.startswith('"') and identifier.endswith('"')) or (
        identifier.startswith("'") and identifier.endswith("'")
    ):
        identifier = identifier[1:-1]

    # Check if this looks like a Confluence page ID (numeric)
    if identifier.isdigit():
        return None, identifier

    # Check for SPACE:Title format
    match = re.match(r"([A-Za-z0-9]+):(.+)", identifier)
    if match:
        space, title = match.groups()
        return space, title

    # If no match, assume it's a title in the default space
    # We can't proceed without a space key, so return None
    logger.warning(f"Invalid Confluence identifier format: {identifier}")
    raise ValueError("Invalid Confluence page identifier. Use 'SPACE:Title' format or a page ID.")


def clean_html_content(html_content: str) -> str:
    """
    Clean HTML content from Confluence to make it more readable as plain text.

    Args:
        html_content: HTML content from Confluence

    Returns:
        Cleaned plain text with proper formatting
    """
    try:
        # Parse HTML using BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()

        # Process specific HTML elements to maintain structure
        # Add line breaks after headings, paragraphs, divs, list items
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "li", "br"]):
            tag.append("\n")

        # Add double line breaks after headings and paragraphs for better separation
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p"]):
            tag.append("\n")

        # Handle lists - add a newline after each list
        for tag in soup.find_all(["ul", "ol"]):
            tag.append("\n")

        # Get text
        text = soup.get_text()

        # Clean up excessive whitespace
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)

        # Join with proper spacing - paragraphs separated by newlines
        text = "\n".join(lines)

        # Fix excessive line breaks (more than 2 consecutive)
        import re

        text = re.sub(r"\n{3,}", "\n\n", text)

        return text
    except Exception as e:
        logger.error(f"Error cleaning HTML content: {e}")
        # Return the original content if cleaning fails
        return html_content


def convert_html_to_markdown(html_content: str) -> str:
    """
    Convert HTML content from Confluence to Markdown format.

    Args:
        html_content: HTML content from Confluence

    Returns:
        Content converted to Markdown format
    """
    try:
        if HTML2TEXT_AVAILABLE:
            # Configure html2text for optimal Markdown conversion
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.ignore_tables = False
            h.ignore_emphasis = False
            h.body_width = 0  # Don't wrap lines

            # Convert HTML to Markdown
            markdown_content = h.handle(html_content)

            # Clean up excessive whitespace
            markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)
            return markdown_content
        else:
            # Fall back to plain text if html2text is not available
            logger.warning("html2text library not available. Using plain text conversion instead.")
            return clean_html_content(html_content)
    except Exception as e:
        logger.error(f"Error converting HTML to Markdown: {e}")
        # Return the plain text version if conversion fails
        return clean_html_content(html_content)


def format_page_for_llm(
    page: Dict[str, Any], include_metadata: bool = True, as_markdown: bool = False
) -> str:
    """
    Format a Confluence page for use as an LLM prompt.

    Args:
        page: Confluence page data
        include_metadata: Whether to include page metadata
        as_markdown: Whether to convert content to Markdown format

    Returns:
        Formatted page content
    """
    try:
        title = page.get("title", "Untitled")

        # Fix the "Space: Unknown" issue by carefully extracting space key
        space = "Unknown"
        if "space" in page and isinstance(page["space"], dict) and "key" in page["space"]:
            space = page["space"]["key"]
        elif "_expandable" in page and "space" in page["_expandable"]:
            # Try to extract from expandable information
            space_path = page["_expandable"].get("space", "")
            if "/" in space_path:
                space = space_path.split("/")[-1]

        # Extract content
        body = page.get("body", {}).get("storage", {}).get("value", "")

        # Process content based on format preference
        if as_markdown:
            content = convert_html_to_markdown(body)
        else:
            content = clean_html_content(body)

        # Format the output
        result = []

        if include_metadata:
            result.append(f"# {title}")
            result.append(f"Space: {space}")

            # Add last updated info if available
            if "version" in page and "when" in page["version"]:
                result.append(f"Last Updated: {page['version']['when']}")

            # Add author info if available
            if "version" in page and "by" in page["version"]:
                author = page["version"]["by"].get("displayName", "Unknown")
                result.append(f"Author: {author}")

            result.append("")  # Blank line before content

        # Add the main content
        result.append(content)

        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error formatting Confluence page: {e}")
        return f"Error formatting Confluence page: {str(e)}"


def fetch_confluence_content(
    identifier: str,
    client: Optional[ConfluenceClient] = None,
    include_metadata: bool = True,
    as_markdown: bool = False,
) -> str:
    """
    Fetch and format a Confluence page by identifier.

    Args:
        identifier: Page identifier (SPACE:Title or ID)
        client: ConfluenceClient instance
        include_metadata: Whether to include page metadata
        as_markdown: Whether to convert content to Markdown format

    Returns:
        Formatted page content
    """
    try:
        # Create client if not provided
        if not client:
            client = ConfluenceClient()

        # Parse the identifier
        space_key, title_or_id = parse_page_identifier(identifier)

        # Fetch the page
        if space_key:
            # We have a space and title
            page = client.get_page_by_title(space_key, title_or_id)
        else:
            # We have a page ID
            page = client.get_page_by_id(title_or_id)

        # Format the page for LLM
        return format_page_for_llm(page, include_metadata, as_markdown)
    except Exception as e:
        logger.error(f"Error fetching Confluence content: {e}")
        return f"Error fetching Confluence content: {str(e)}"


def search_confluence(
    cql: str,
    client: Optional[ConfluenceClient] = None,
    include_metadata: bool = True,
    max_results: int = 5,
    as_markdown: bool = False,
    include_content: bool = True,
    fetch_full_content: bool = False,
) -> str:
    """
    Search Confluence using CQL and format results.

    Args:
        cql: Confluence Query Language query
        client: ConfluenceClient instance
        include_metadata: Whether to include page metadata
        max_results: Maximum number of results to return
        as_markdown: Whether to convert content to Markdown format
        include_content: Whether to include content from search results
        fetch_full_content: Whether to fetch full content of each page (may require additional API calls)

    Returns:
        Formatted search results
    """
    try:
        # Create client if not provided
        if not client:
            client = ConfluenceClient()

        # Search Confluence
        results = client.search_pages(cql, limit=max_results)

        if not results:
            return "No Confluence pages found matching the query."

        # Format results
        formatted_results = []

        for i, result in enumerate(results, 1):
            # Extract content
            content = result.get("content", {})
            title = content.get("title", "Untitled")

            formatted_results.append(f"## Result {i}: {title}")

            # Always include basic metadata
            space = "Unknown"
            if (
                "space" in content
                and isinstance(content["space"], dict)
                and "key" in content["space"]
            ):
                space = content["space"]["key"]

            formatted_results.append(f"Space: {space}")

            page_id = None
            if "id" in content:
                page_id = content["id"]
                formatted_results.append(f"ID: {page_id}")

            if "version" in content and "when" in content["version"]:
                formatted_results.append(f"Last Updated: {content['version']['when']}")

            if "version" in content and "by" in content["version"]:
                author = content["version"]["by"].get("displayName", "Unknown")
                formatted_results.append(f"Author: {author}")

            if include_content:
                # Check if we need to fetch full content
                if fetch_full_content and page_id:
                    try:
                        # Fetch the complete page content using the ID
                        logger.info(f"Fetching full content for page: {title} (ID: {page_id})")
                        full_page = client.get_page_by_id(page_id)
                        formatted_results.append("")  # Add blank line before content
                        formatted_results.append("### Full Content:")
                        # Format the full page content
                        full_content = format_page_for_llm(
                            full_page, include_metadata=False, as_markdown=as_markdown
                        )
                        formatted_results.append(full_content)
                    except Exception as e:
                        logger.error(f"Error fetching full content for page {page_id}: {e}")
                        formatted_results.append("")
                        formatted_results.append("Error fetching full content for this page.")
                else:
                    # Use the content from search results
                    search_content = format_page_for_llm(
                        content, include_metadata=False, as_markdown=as_markdown
                    )
                    if search_content.strip():  # Only add if there's actual content
                        formatted_results.append("")  # Add blank line before content
                        formatted_results.append("### Content from search result:")
                        formatted_results.append(search_content)

            # Add separator between results
            if i < len(results):
                formatted_results.append("\n---\n")

        return "\n".join(formatted_results)
    except Exception as e:
        logger.error(f"Error searching Confluence: {e}")
        return f"Error searching Confluence: {str(e)}"
