"""
IPython magic command for displaying and processing images.

This module provides a magic command for displaying and processing images in IPython notebooks.
It supports image resizing, quality adjustment, and format conversion for compatibility with LLM providers.
"""

import logging
import os

# IPython imports with fallback handling
try:
    from IPython.core.magic import line_magic, magics_class
    from IPython.core.magic_arguments import argument, magic_arguments

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

    # Define dummy decorators if IPython is not installed
    def magics_class(cls):
        return cls

    def line_magic(func):
        return func

    def magic_arguments():
        return lambda func: func

    def argument(*args, **kwargs):
        return lambda func: func


# Import image utilities
from cellmage.integrations.image_utils import (
    format_image_for_llm,
    format_image_info_for_display,
    format_processed_image_info,
    get_image_processor,
    is_image_processing_available,
)

# Import the base magic class
from cellmage.magic_commands.tools.base_tool_magic import BaseMagics

# Create a logger
logger = logging.getLogger(__name__)


@magics_class
class ImageMagics(BaseMagics):
    """IPython magic commands for displaying and processing images."""

    def __init__(self, shell):
        super().__init__(shell)
        self._image_processor = get_image_processor() if is_image_processing_available() else None

    @magic_arguments()
    @argument(
        "image_path",
        help="Path to the image file to process",
    )
    @argument(
        "--resize",
        "-r",
        type=int,
        default=None,
        help="Width to resize the image to (maintains aspect ratio)",
    )
    @argument(
        "--quality",
        "-q",
        type=float,
        default=None,
        help="Quality for lossy image formats (0.0-1.0)",
    )
    @argument(
        "--show",
        action="store_true",
        help="Display the image inline after processing",
    )
    @argument(
        "--info",
        "-i",
        action="store_true",
        help="Display information about the image",
    )
    @argument(
        "--add-to-chat",
        "-a",
        action="store_true",
        help="Add the image to the current chat session (default: always added to history/context)",
    )
    @argument(
        "--convert",
        "-c",
        action="store_true",
        help="Force conversion to a compatible format",
    )
    @argument(
        "--format",
        "-f",
        type=str,
        default=None,
        help="Format to convert the image to",
    )
    @line_magic
    def img(self, line):
        """
        Process an image for LLM context and optionally display it.

        Usage:
            %img path/to/image.png [--resize WIDTH] [--quality Q] [--show] [--info] [--convert] [--format FMT]
        """
        from IPython.core.magic_arguments import parse_argstring
        from IPython.display import Image as IPyImage
        from IPython.display import display

        if not _IPYTHON_AVAILABLE:
            logger.error("IPython is not available. Cannot process images.")
            return "Error: IPython is not available. Cannot process images."
        if not is_image_processing_available():
            logger.error("Image processing is not available. Install PIL with 'pip install pillow'")
            return "Error: Image processing is not available. Install PIL with 'pip install pillow'"

        args = parse_argstring(self.img, line)
        image_path = os.path.abspath(os.path.expanduser(args.image_path))
        if not os.path.isfile(image_path):
            logger.error(f"Image file not found: {image_path}")
            return f"Error: Image file not found: {image_path}"
        try:
            if self._image_processor is None:
                self._image_processor = get_image_processor()
                if self._image_processor is None:
                    logger.error("Failed to initialize image processor")
                    return "Error: Failed to initialize image processor"
            image_info = self._image_processor.get_image_info(image_path)
            image_data, mime_type, metadata = self._image_processor.process_image(
                image_path,
                width=args.resize,
                quality=args.quality,
                target_format=args.format if args.format else None,
            )
            # Only display the image if --show is passed
            if args.show:
                display(IPyImage(data=image_data.getvalue(), format=mime_type.split("/")[-1]))
            # Display info if requested
            if args.info:
                print(format_image_info_for_display(image_info))
                if args.resize or args.quality or args.convert or args.format:
                    print(format_processed_image_info(image_info, metadata))
            # Always add image to conversation history and LLM context
            chat_manager = self._get_chat_manager()
            if (
                chat_manager
                and hasattr(chat_manager, "conversation_manager")
                and hasattr(chat_manager.conversation_manager, "add_message")
            ):
                llm_image = format_image_for_llm(image_data, mime_type, metadata)
                from cellmage.models import Message

                msg = Message(
                    role="user",
                    content="[Image sent]",
                    metadata={"source": image_path, "llm_image": llm_image, **metadata},
                )
                chat_manager.conversation_manager.add_message(msg)
            else:
                logger.warning(
                    "Chat manager or conversation manager not available. Could not add image to history."
                )
            # Align output to other magics: only print a short status line
            return f"✅ {os.path.basename(image_path)} processed and added to conversation history."
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}", exc_info=True)
            return f"Error processing image: {str(e)}"


def load_ipython_extension(ipython):
    """
    Load the extension in IPython.
    """
    if not _IPYTHON_AVAILABLE:
        logger.warning("IPython not available. Image magic commands are disabled.")
        return
    ipython.register_magics(ImageMagics)
