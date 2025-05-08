# 🖼️ Image Utilities

The `cellmage.utils.image_utils` module provides a comprehensive set of utilities for processing, formatting, and managing images for use with Large Language Models (LLMs). This module is the foundation for the `%img` magic command and handles all the image processing functionality.

## Key Components

### `ImageProcessor` Class

The central class for image processing operations. It handles:

- Loading images from files
- Resizing while maintaining aspect ratios
- Format conversion
- Quality adjustment
- Metadata extraction
- Base64 encoding for LLM API compatibility

### Utility Functions

The module also provides several helper functions:

- `is_image_processing_available()`: Checks if required dependencies are installed
- `get_image_processor()`: Factory function to create an ImageProcessor instance
- `format_image_info_for_display()`: Formats image metadata for user-friendly display
- `format_processed_image_info()`: Formats comparison between original and processed images
- `format_image_for_llm()`: Prepares image data for LLM API consumption

## Usage Examples

### Basic Image Processing

```python
from cellmage.utils.image_utils import get_image_processor

# Create an image processor
processor = get_image_processor()
if processor:
    # Get basic image info
    image_info = processor.get_image_info("path/to/image.jpg")

    # Process an image (resize, convert, adjust quality)
    image_data, mime_type, metadata = processor.process_image(
        "path/to/image.jpg",
        width=800,  # Resize to 800px width
        quality=0.85,  # 85% quality
        target_format="webp"  # Convert to WebP
    )

    # Format for display
    info_display = format_image_info_for_display(image_info)
    print(info_display)
```

### Preparing Images for LLMs

```python
from cellmage.utils.image_utils import format_image_for_llm, get_image_processor

# Process an image
processor = get_image_processor()
image_data, mime_type, metadata = processor.process_image("path/to/image.jpg")

# Format for LLM API
llm_image = format_image_for_llm(image_data, mime_type, metadata)

# llm_image can now be used with the OpenAI API or other LLM providers
```

## Implementation Details

### Dependencies

The module relies on the Pillow (PIL) library for image processing:

```python
try:
    from PIL import Image, UnidentifiedImageError
    _IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    _IMAGE_PROCESSING_AVAILABLE = False
```

### Format Handling

The module handles multiple image formats:

- **JPEG/JPG**: Optimized with quality settings
- **PNG**: Optimized for size
- **WebP**: Modern format with excellent compression
- Other formats: Converted to compatible formats as needed

### Error Handling

The utilities include robust error handling for common image processing issues:

- File not found
- Unidentified image formats
- Processing errors
- Dependency missing errors

## API Reference

### `ImageProcessor` Methods

#### `__init__(self)`
Initialize the image processor and check for dependencies.

#### `process_image(self, image_path, width=None, quality=None, target_format=None)`
Process an image for optimal use with LLMs.

**Arguments:**
- `image_path`: Path to the image file
- `width`: Width to resize the image to (maintains aspect ratio)
- `quality`: Quality for lossy image formats (0.0-1.0)
- `target_format`: Format to convert the image to

**Returns:**
- `BytesIO` object containing the processed image data
- MIME type of the processed image
- Metadata dictionary with information about the original and processed image

#### `encode_image_base64(self, image_data)`
Encode image data as base64 for API compatibility.

**Arguments:**
- `image_data`: BytesIO object containing image data

**Returns:**
- Base64 encoded string of the image data

#### `get_image_info(self, image_path)`
Get basic information about an image.

**Arguments:**
- `image_path`: Path to the image file

**Returns:**
- Dictionary with basic image info (dimensions, format, size)

### Helper Functions

#### `is_image_processing_available()`
Check if required image processing libraries are available.

**Returns:**
- Boolean indicating availability of image processing dependencies

#### `get_image_processor()`
Create and return an ImageProcessor instance if dependencies are available.

**Returns:**
- ImageProcessor instance or None if dependencies are missing

#### `format_image_info_for_display(image_info)`
Format image information for user-friendly display.

**Arguments:**
- `image_info`: Dictionary with image information

**Returns:**
- Formatted string with image information

#### `format_processed_image_info(original_info, processed_info)`
Format information comparing original and processed images.

**Arguments:**
- `original_info`: Dictionary with original image information
- `processed_info`: Dictionary with processed image information

**Returns:**
- Formatted string with comparison information

#### `format_image_for_llm(image_data, mime_type, metadata)`
Format image for use with LLM API.

**Arguments:**
- `image_data`: BytesIO object with image data
- `mime_type`: MIME type of the image
- `metadata`: Dictionary with image metadata

**Returns:**
- Dictionary with image information formatted for LLM API use
