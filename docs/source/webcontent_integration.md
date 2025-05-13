# WebContent Integration

CellMage provides a powerful integration for fetching and processing website content, allowing you to extract information from web pages directly into your Jupyter notebooks and use it as context for your LLM prompts.

## Installation

To use the WebContent integration, install CellMage with the `webcontent` extra:

```bash
pip install "cellmage[webcontent]"
```

This will install the necessary dependencies:
- `requests`: For HTTP requests
- `beautifulsoup4`: For HTML parsing
- `markdownify`: For HTML to Markdown conversion
- `trafilatura`: For advanced content extraction

You can also install these dependencies separately:

```bash
pip install requests beautifulsoup4 markdownify trafilatura
```

## Basic Usage

Load the extension in your Jupyter notebook:

```ipython
%load_ext cellmage.magic_commands.tools.webcontent_magic
```

This will register the `%webcontent` magic command.

To fetch content from a website:

```ipython
%webcontent https://example.com
```

This will automatically:
1. Fetch the website's HTML content
2. Clean and extract the main content (removing navigation, ads, etc.)
3. Convert the content to Markdown format
4. Add it to your conversation history as a user message, making it available as context for your LLM prompts

## Advanced Usage

### Content Extraction Methods

The WebContent integration offers three different methods for extracting content from websites:

1. **trafilatura** (default): Uses the Trafilatura library, which is specifically designed for content extraction and works well on most websites
2. **bs4**: Uses BeautifulSoup to identify and extract the main content area of the page
3. **simple**: Simply converts the entire HTML to Markdown with minimal cleaning

You can specify which method to use:

```ipython
# Use BeautifulSoup for extraction
%webcontent https://example.com --method bs4

# Use simple extraction
%webcontent https://example.com --method simple
```

### Raw HTML Option

If you prefer to get the raw HTML content without cleaning or extraction:

```ipython
%webcontent https://example.com --raw
```

### Media and Link Options

You can control how images and links are handled:

```ipython
# Include image references in the output
%webcontent https://example.com --include-images

# Remove hyperlinks from the output
%webcontent https://example.com --no-links
```

### Network Options

Adjust the request timeout if needed:

```ipython
# Set a custom timeout in seconds
%webcontent https://example.com --timeout 60
```

### Command Options

| Option             | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| `--system`         | Add the content as a system message instead of a user message      |
| `--show`           | Just display the content without adding it to conversation history |
| `--clean`          | Clean and extract main content (default behavior)                  |
| `--raw`            | Get raw HTML content without cleaning                              |
| `--method METHOD`  | Content extraction method: trafilatura (default), bs4, or simple   |
| `--include-images` | Include image references in the output                             |
| `--no-links`       | Remove hyperlinks from the output                                  |
| `--timeout N`      | Request timeout in seconds (default: 30)                           |

### Examples

Fetch website content with default settings (clean content as Markdown):
```ipython
%webcontent https://example.com
```

Fetch raw HTML content:
```ipython
%webcontent https://example.com --raw
```

Fetch content and add it as system context:
```ipython
%webcontent https://example.com --system
```

Just display content without adding to history:
```ipython
%webcontent https://example.com --show
```

Use BeautifulSoup for extraction and include images:
```ipython
%webcontent https://example.com --method bs4 --include-images
```

## Using WebContent with LLM Queries

After fetching website content, you can reference it in your LLM prompts:

```ipython
# First, fetch the website content
%webcontent https://example.com

# Then, ask the LLM about it
%%llm
Summarize the key points from the website content above.
```

You can also combine WebContent with other integrations:

```ipython
# Fetch project documentation from a website
%webcontent https://example.com/docs --system

# Fetch a GitHub repository
%github username/repo

# Ask LLM to analyze both
%%llm
Compare the repository code with the documentation website.
Are there any inconsistencies or missing features?
```

## Troubleshooting

### Connection Issues

1. **Connection errors**:
   - Check if the website is accessible in your browser
   - Verify your network connection
   - Some websites might be blocking requests from scripts or have rate limiting
   - Try increasing the timeout: `%webcontent https://example.com --timeout 60`

2. **SSL/TLS errors**:
   - Some websites might have certificate issues
   - If you trust the website, consult the requests library documentation for SSL verification options

### Content Extraction Issues

1. **Poor content extraction**:
   - Try a different extraction method: `%webcontent https://example.com --method bs4`
   - If all extraction methods fail, try raw mode: `%webcontent https://example.com --raw`
   - Some websites use complex JavaScript to render content, which might not be accessible through simple HTTP requests

2. **Missing images or links**:
   - By default, images are excluded. Use `--include-images` to include them
   - Check if the links are relative paths, which might not work out of context

3. **Very large content**:
   - Some websites have a lot of content which might increase token usage with your LLM
   - Consider using more specific URLs that point to specific pages or sections

For persistent issues, enable debug logging:

```ipython
import logging
from cellmage.utils.logging import setup_logging
setup_logging(level=logging.DEBUG)
# The logs will be written to cellmage.log in your working directory
```
