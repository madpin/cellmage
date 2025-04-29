"""
IPython-specific context provider for CellMage.

This module provides an implementation of the ContextProvider interface
that works with IPython/Jupyter environments.
"""

import logging
import uuid
from typing import Any, Dict, Optional, Tuple

# Set up logging
logger = logging.getLogger(__name__)

# Try to import IPython dependencies with fallbacks
try:
    from IPython import get_ipython  # noqa: E402
    from IPython.display import HTML, Markdown, clear_output, display  # noqa: E402

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

# Make ipywidgets optional
_WIDGETS_AVAILABLE = False
try:
    import ipywidgets as widgets  # noqa: E402

    _WIDGETS_AVAILABLE = True
except ImportError:
    logger.debug("ipywidgets not available, falling back to simpler display methods")

# Import from parent package
from ..interfaces import ContextProvider  # noqa: E402


class IPythonContextProvider(ContextProvider):
    """
    Implementation of the ContextProvider interface for IPython/Jupyter environments.

    This class provides methods to:
    - Display LLM responses in Markdown format
    - Display status information in a styled HTML box
    - Get execution context from the IPython environment
    """

    def __init__(self):
        """Initialize the context provider."""
        self._ipython = get_ipython() if _IPYTHON_AVAILABLE else None
        self._display_handles = {}  # Store display handles for updating

    def display_markdown(self, content: str) -> None:
        """
        Display content as Markdown in the notebook.

        Args:
            content: The markdown content to display
        """
        if not _IPYTHON_AVAILABLE:
            print(content)
            return

        try:
            display(Markdown(content))
        except Exception as e:
            logger.error(f"Error displaying markdown content: {e}")
            # Fallback to plain text
            print(content)

    def display_response(self, content: str) -> None:
        """
        Display an assistant response in the user interface.

        Args:
            content: Response content to display
        """
        # For IPython, we'll use the same display_markdown method
        # but we could add styling specific to assistant responses
        self.display_markdown(content)

    def display_stream_start(self) -> Any:
        """
        Set up display for a streaming response.

        Returns:
            An object that can be used to update the display
        """
        if not _IPYTHON_AVAILABLE:
            # For non-IPython environments, return a simple placeholder
            print("(Streaming response started...)")
            return {"content": ""}

        try:
            # Generate a unique ID for this stream
            stream_id = str(uuid.uuid4().hex)

            # Set up the base content for tracking accumulated output
            stream_obj = {"content": "", "id": stream_id}

            if _WIDGETS_AVAILABLE:
                # Try ipywidgets approach first
                try:
                    # Use Output widget for widgetized display
                    out = widgets.Output()
                    display(out)
                    stream_obj["widget"] = out
                    return stream_obj
                except Exception as e:
                    logger.debug(f"Widget display failed, falling back: {e}")
                    # Fall through to simpler approach

            # Simple approach using direct display
            # Display initial empty markdown that we'll update
            display(Markdown(""))

            # Store the stream object for tracking content
            self._display_handles[stream_id] = True

            return stream_obj
        except Exception as e:
            logger.error(f"Error setting up stream display: {e}")
            # Emergency fallback
            print("(Streaming response started...)")
            return {"content": ""}

    def update_stream(self, display_object: Any, content: str) -> None:
        """
        Update a streaming display with new content.

        Args:
            display_object: The display object from display_stream_start
            content: The content to display
        """
        if not _IPYTHON_AVAILABLE or not display_object:
            # For non-IPython environments or if display failed to initialize
            print(content, end="", flush=True)
            return

        try:
            # Append new content to existing accumulated content
            if isinstance(display_object, dict):
                display_object["content"] += content
                accumulated_content = display_object["content"]
            else:
                accumulated_content = content

            # Try widgets approach first if available
            if (
                _WIDGETS_AVAILABLE
                and isinstance(display_object, dict)
                and "widget" in display_object
            ):
                with display_object["widget"]:
                    clear_output(wait=True)
                    display(Markdown(accumulated_content))
                return

            # For non-widget approach, use standard display with clear_output
            clear_output(wait=True)
            display(Markdown(accumulated_content))

        except Exception as e:
            logger.error(f"Error updating stream display: {e}")
            # Emergency fallback - print to console
            print(content, end="", flush=True)

    def display_status(self, status_info: Dict[str, Any]) -> None:
        """
        Display status information in a styled HTML box.

        Args:
            status_info: Dictionary with status information
        """
        if not _IPYTHON_AVAILABLE:
            # Fallback for non-IPython environments
            parts = []
            for key, value in status_info.items():
                if value is not None:
                    parts.append(f"{key}: {value}")
            print(" | ".join(parts))
            return

        duration = status_info.get("duration", 0.0)
        success = status_info.get("success", False)
        tokens_in = status_info.get("tokens_in")
        tokens_out = status_info.get("tokens_out")
        cost_str = status_info.get("cost_str")
        model_used = status_info.get("model_used")

        # Create a more compact status display
        icon = "✓" if success else "⚠"
        model_text = f" {model_used}" if model_used else ""
        tokens_text = ""
        if tokens_in is not None or tokens_out is not None:
            in_txt = f"{tokens_in}↓" if tokens_in is not None else "?"
            out_txt = f"{tokens_out}↑" if tokens_out is not None else "?"
            tokens_text = f" • {in_txt}/{out_txt} tokens"

        cost_text = f" • ${cost_str}" if cost_str else ""

        # Single unified status text
        status_text = f"{icon}{model_text} • {duration:.2f}s{tokens_text}{cost_text}"

        # Style based on success status
        if success:
            bg_color, text_color = "#f1f8e9", "#33691e"  # Light green bg, dark green text
            border_color = "#c5e1a5"  # Light green border
        else:
            bg_color, text_color = "#ffebee", "#c62828"  # Light red bg, darker red text
            border_color = "#ef9a9a"  # Light red border

        status_html = f"""
        <div style="background-color: {bg_color}; border: 1px solid {border_color}; color: {text_color};
                    padding: 3px 6px; margin-top: 4px; border-radius: 3px; font-family: monospace; 
                    font-size: 0.75em; line-height: 1.2; display: inline-block; opacity: 0.85;">
            {status_text}
        </div>
        """
        try:
            display(HTML(status_html))
        except Exception:
            # Fallback if display fails
            print(f"Status: {status_text}")

    def get_cell_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the current execution context.

        Returns:
            Dict with context information including:
                - cell_id: ID of the current cell
                - execution_count: Current execution count
        """
        result = {"cell_id": None, "execution_count": None}

        if not _IPYTHON_AVAILABLE or not self._ipython:
            return result

        # Try to get the parent header from the IPython shell
        try:
            parent = self._ipython.get_parent()
            if parent and "metadata" in parent:
                metadata = parent["metadata"]
                result["cell_id"] = metadata.get("cellId")
        except Exception as e:
            logger.debug(f"Error getting cell ID: {e}")

        # Try to get the execution count
        try:
            result["execution_count"] = self._ipython.execution_count
        except Exception as e:
            logger.debug(f"Error getting execution count: {e}")

        return result

    def get_execution_context(self) -> Tuple[Optional[int], Optional[str]]:
        """
        Get the current execution context.

        Returns:
            Tuple of (execution_count, cell_id)
        """
        metadata = self.get_cell_metadata()
        return (metadata.get("execution_count"), metadata.get("cell_id"))

    def is_ipython_available(self) -> bool:
        """Check if IPython is available."""
        return _IPYTHON_AVAILABLE


# Create a singleton instance
_instance: Optional[IPythonContextProvider] = None


def get_ipython_context_provider() -> IPythonContextProvider:
    """Get or create the singleton IPythonContextProvider instance."""
    global _instance
    if _instance is None:
        _instance = IPythonContextProvider()
    return _instance
