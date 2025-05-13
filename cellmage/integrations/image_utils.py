"""
Utility functions for image processing and manipulation.

This module provides utilities for processing images for use with LLMs.
"""

import base64
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from cellmage.config import settings

# Import image processing libraries with availability checking
_IMAGE_PROCESSING_AVAILABLE = False
try:
    from PIL import Image, UnidentifiedImageError

    _IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    pass


logger = logging.getLogger(__name__)


class ImageProcessor:
    """Helper class to process images for LLM usage."""

    def __init__(self):
        """Initialize the image processor."""
        if not _IMAGE_PROCESSING_AVAILABLE:
            logger.warning("Required libraries for image processing not available.")
            raise ImportError(
                "Required libraries for image processing not available. "
                "Install them with 'pip install pillow'"
            )

    def process_image(
        self,
        image_path: Union[str, Path],
        width: Optional[int] = None,
        quality: Optional[float] = None,
        target_format: Optional[str] = None,
    ) -> Tuple[BytesIO, str, Dict[str, Any]]:
        """
        Process an image for use with LLMs.

        Args:
            image_path: Path to the image file
            width: Width to resize the image to (maintaining aspect ratio)
            quality: Quality for image compression (0.0-1.0)
            target_format: Format to convert the image to

        Returns:
            Tuple containing:
            - BytesIO object with the processed image
            - MIME type of the processed image
            - Metadata dictionary with information about the original and processed image
        """
        # Default values from settings
        width = width or settings.image_default_width
        quality = quality or settings.image_default_quality
        target_format = target_format or settings.image_target_format

        # Normalize path
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        # Get original format
        original_format = path.suffix.lower().lstrip(".")
        final_format = original_format

        # Open the image
        try:
            with Image.open(path) as img:
                original_width, original_height = img.size

                # Determine if format conversion is needed
                if original_format not in settings.image_formats_llm_compatible:
                    final_format = target_format
                    logger.info(f"Converting image from {original_format} to {final_format}")

                # Calculate new height to maintain aspect ratio
                if width and width != original_width:
                    ratio = width / original_width
                    new_height = int(original_height * ratio)
                    img = img.resize((width, new_height), Image.LANCZOS)
                    logger.info(
                        f"Resized image from {original_width}x{original_height} to {width}x{new_height}"
                    )

                # Save to BytesIO
                output = BytesIO()

                # Handle format-specific save parameters
                save_params = {}
                if final_format.lower() in ["jpg", "jpeg"]:
                    save_params["quality"] = int(quality * 100)  # PIL uses 1-100 scale
                    save_params["optimize"] = True
                    save_params["format"] = "JPEG"
                elif final_format.lower() == "png":
                    save_params["optimize"] = True
                    save_params["format"] = "PNG"
                elif final_format.lower() == "webp":
                    save_params["quality"] = int(quality * 100)  # 0-100 scale
                    save_params["format"] = "WEBP"
                else:
                    save_params["format"] = final_format.upper()

                img.save(output, **save_params)
                output.seek(0)  # Reset file pointer

                # Create metadata
                metadata = {
                    "original_path": str(path),
                    "original_size": path.stat().st_size,
                    "original_dimensions": (original_width, original_height),
                    "processed_dimensions": img.size,
                    "processed_size": output.getbuffer().nbytes,
                    "original_format": original_format,
                    "processed_format": final_format,
                    "quality": quality,
                    "converted": original_format != final_format,
                }

                # Determine MIME type
                mime_mapping = {
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp",
                    "gif": "image/gif",
                }
                mime_type = mime_mapping.get(final_format.lower(), f"image/{final_format}")

                return output, mime_type, metadata

        except UnidentifiedImageError:
            raise ValueError(f"Could not identify image format for {path}")
        except Exception as e:
            raise Exception(f"Error processing image {path}: {str(e)}")

    def encode_image_base64(self, image_data: BytesIO) -> str:
        """
        Encode image data to base64.

        Args:
            image_data: BytesIO object containing the image data

        Returns:
            Base64 encoded string of the image data
        """
        image_data.seek(0)  # Ensure we're at the start
        encoded = base64.b64encode(image_data.getvalue()).decode("utf-8")
        return encoded

    def get_image_info(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get basic information about an image.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with basic image info (dimensions, format, size)
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        try:
            with Image.open(path) as img:
                info = {
                    "path": str(path),
                    "filename": path.name,
                    "format": img.format.lower() if img.format else path.suffix.lower().lstrip("."),
                    "dimensions": img.size,
                    "mode": img.mode,
                    "file_size": path.stat().st_size,
                }
                return info
        except Exception as e:
            raise Exception(f"Error getting image info for {path}: {str(e)}")


def format_image_info_for_display(image_info: Dict[str, Any]) -> str:
    """
    Format image information for display.

    Args:
        image_info: Dictionary with image information

    Returns:
        Formatted string with image information
    """
    width, height = image_info.get("dimensions", (0, 0))
    size_kb = image_info.get("file_size", 0) / 1024

    info = f"Image: {image_info.get('filename', 'Unknown')}\n"
    info += f"• Format: {image_info.get('format', 'Unknown').upper()}\n"
    info += f"• Dimensions: {width} × {height} pixels\n"
    info += f"• Mode: {image_info.get('mode', 'Unknown')}\n"
    info += f"• Size: {size_kb:.1f} KB\n"
    info += f"• Path: {image_info.get('path', 'Unknown')}\n"

    return info


def format_processed_image_info(
    original_info: Dict[str, Any], processed_info: Dict[str, Any]
) -> str:
    """
    Format information about original and processed images.

    Args:
        original_info: Dictionary with original image information
        processed_info: Dictionary with processed image information

    Returns:
        Formatted string with comparison information
    """
    orig_width, orig_height = original_info.get("original_dimensions", (0, 0))
    proc_width, proc_height = original_info.get("processed_dimensions", (0, 0))

    orig_size_kb = original_info.get("original_size", 0) / 1024
    proc_size_kb = original_info.get("processed_size", 0) / 1024

    size_reduction = (1 - (proc_size_kb / orig_size_kb)) * 100 if orig_size_kb > 0 else 0

    info = f"Image processed: {os.path.basename(original_info.get('original_path', 'Unknown'))}\n"
    info += f"• Original: {orig_width}×{orig_height} pixels, {orig_size_kb:.1f} KB, {original_info.get('original_format', 'Unknown').upper()}\n"
    info += f"• Processed: {proc_width}×{proc_height} pixels, {proc_size_kb:.1f} KB, {original_info.get('processed_format', 'Unknown').upper()}\n"
    info += f"• Size reduction: {size_reduction:.1f}%\n"

    if original_info.get("converted", False):
        info += f"• Converted: {original_info.get('original_format', 'Unknown').upper()} → {original_info.get('processed_format', 'Unknown').upper()}\n"

    return info


def format_image_for_llm(
    image_data: BytesIO, mime_type: str, metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Format image for use with LLM API.

    Args:
        image_data: BytesIO object with image data
        mime_type: MIME type of the image
        metadata: Dictionary with image metadata

    Returns:
        Dictionary with image information for LLM API
    """
    # Get a processor to encode the image
    processor = ImageProcessor()
    base64_image = processor.encode_image_base64(image_data)

    # Format for OpenAI
    return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}


# Helper function to check if required libraries are available
def is_image_processing_available() -> bool:
    """Check if required image processing libraries are available."""
    return _IMAGE_PROCESSING_AVAILABLE


# Factory function to create an ImageProcessor
def get_image_processor() -> Optional[ImageProcessor]:
    """
    Create and return an ImageProcessor instance if dependencies are available.

    Returns:
        ImageProcessor instance or None if dependencies are missing
    """
    if _IMAGE_PROCESSING_AVAILABLE:
        try:
            return ImageProcessor()
        except Exception as e:
            logger.error(f"Error creating ImageProcessor: {e}")
    return None
