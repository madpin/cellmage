"""
Utility functions for fetching and processing website content.

This module provides utilities for fetching and extracting content from websites.
"""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

# Import website parsing libraries with availability checking
_WEBSITE_PARSING_AVAILABLE = False
try:
    import markdownify
    import requests
    import trafilatura
    from bs4 import BeautifulSoup

    _WEBSITE_PARSING_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)


class WebsiteContentFetcher:
    """Helper class to fetch and process website content."""

    def __init__(self):
        """Initialize the website content fetcher."""
        if not _WEBSITE_PARSING_AVAILABLE:
            logger.warning("Required libraries for website content fetching not available.")
            raise ImportError(
                "Required libraries for website content fetching not available. "
                "Install them with 'pip install requests beautifulsoup4 markdownify trafilatura'"
            )

    def fetch_url(self, url: str, timeout: int = 30) -> Optional[str]:
        """Fetch the content of a URL.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Raw HTML content or None if fetch failed
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return None

    def clean_content(
        self,
        html: str,
        extraction_method: str = "trafilatura",
        include_images: bool = False,
        include_links: bool = True,
    ) -> str:
        """Extract and clean the main content from HTML.

        Args:
            html: Raw HTML content
            extraction_method: Method to use for extraction ('trafilatura', 'bs4', or 'simple')
            include_images: Whether to include images in the output
            include_links: Whether to include links in the output

        Returns:
            Cleaned content as markdown
        """
        if extraction_method == "trafilatura":
            try:
                # Trafilatura is generally the best option for extracting main content
                content = trafilatura.extract(
                    html,
                    include_images=include_images,
                    include_links=include_links,
                    output_format="markdown",
                )
                if content:
                    return content
                # Fall back to BS4 if trafilatura doesn't extract anything
                logger.warning("Trafilatura extraction failed, falling back to BS4")
            except Exception as e:
                logger.error(f"Error with trafilatura extraction: {e}")
                logger.warning("Falling back to BS4 extraction")

        if extraction_method == "trafilatura" or extraction_method == "bs4":
            try:
                soup = BeautifulSoup(html, "html.parser")

                # Remove script, style, and other non-content elements
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()

                # Convert to markdown
                md_converter = markdownify.MarkdownConverter(
                    strip=["script", "style", "nav", "footer", "header", "aside"],
                    heading_style="atx",
                    bullet_char="-",
                    escape_asterisks=True,
                )
                if not include_images:
                    for img in soup.find_all("img"):
                        img.decompose()

                if not include_links:
                    # Convert links to plain text
                    for a in soup.find_all("a"):
                        a.replace_with(a.text)

                # Try to find the main content
                main_content = None
                for selector in [
                    "main",
                    "article",
                    "#content",
                    ".content",
                    "#main",
                    ".main",
                    "#article",
                    ".article",
                ]:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break

                if main_content:
                    return md_converter.convert(str(main_content))
                else:
                    # If no main content found, use the body
                    return md_converter.convert(str(soup.body))
            except Exception as e:
                logger.error(f"Error with BS4 extraction: {e}")
                logger.warning("Falling back to simple extraction")

        # Simple extraction - just convert everything
        try:
            soup = BeautifulSoup(html, "html.parser")
            md_converter = markdownify.MarkdownConverter()
            return md_converter.convert(str(soup))
        except Exception as e:
            logger.error(f"Error with simple extraction: {e}")
            return "Error: Could not extract content from website"

    def get_site_info(self, url: str, html: str) -> Dict[str, Any]:
        """Extract basic metadata from the website.

        Args:
            url: URL of the website
            html: Raw HTML content

        Returns:
            Dictionary with metadata
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title = soup.title.string.strip() if soup.title else "Unknown Title"

            # Extract description
            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and "content" in meta_desc.attrs:
                description = meta_desc["content"].strip()

            # Extract domain
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            return {
                "title": title,
                "description": description,
                "domain": domain,
                "url": url,
                "fetched_at": "",  # Will be filled in by the caller
            }
        except Exception as e:
            logger.error(f"Error extracting site info: {e}")
            return {
                "title": "Unknown Title",
                "description": "",
                "domain": urlparse(url).netloc if url else "unknown",
                "url": url,
                "fetched_at": "",
            }


def format_website_content_for_display(content: str, metadata: Dict[str, Any]) -> str:
    """Format website content for terminal display.

    Args:
        content: The website content
        metadata: Website metadata

    Returns:
        Formatted content
    """
    formatted_content = f"# {metadata['title']}\n"
    formatted_content += f"*Source: {metadata['url']}*\n\n"

    if metadata["description"]:
        formatted_content += f"**Description**: {metadata['description']}\n\n"

    formatted_content += "---\n\n"
    formatted_content += content

    return formatted_content


def format_website_content_for_llm(content: str, metadata: Dict[str, Any]) -> str:
    """Format website content for LLM.

    Args:
        content: The website content
        metadata: Website metadata

    Returns:
        Formatted content
    """
    # Similar to display format but might be optimized for LLM consumption
    return format_website_content_for_display(content, metadata)


# Helper function to check if required libraries are available
def is_website_parsing_available() -> bool:
    """Check if required libraries for website parsing are available.

    Returns:
        True if all required libraries are available, False otherwise
    """
    return _WEBSITE_PARSING_AVAILABLE


# Factory function to create a WebsiteContentFetcher
def get_website_content_fetcher() -> Optional[WebsiteContentFetcher]:
    """Get a WebsiteContentFetcher instance if the required libraries are available.

    Returns:
        WebsiteContentFetcher instance or None if required libraries are not available
    """
    try:
        return WebsiteContentFetcher()
    except ImportError:
        logger.warning("Required libraries for website content fetching not available.")
        return None
