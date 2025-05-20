# 🖼️ Image Magic Integration

The Image Magic integration provides an easy way to process, display, and incorporate images into your LLM conversations within IPython notebooks. This feature is implemented through the `%img` magic command and relies on the `ImageProcessor` class and utility functions from the `cellmage.utils.image_utils` module.

## Features

- **Display images** directly in your notebook
- **Resize images** while maintaining aspect ratios
- **Convert image formats** for optimal LLM compatibility
- **Adjust image quality** for lossy formats
- **View detailed image metadata**
- **Add images to LLM context** automatically
- **Base64 encoding** for LLM API compatibility

## Installation Requirements

The Image Magic integration requires the Pillow library:

```bash
pip install pillow
```

## Using the `%img` Magic Command

### Basic Usage

```text
%img path/to/image.jpg
```

This command processes the image and adds it to your conversation history/context, allowing the LLM to "see" and analyze the image in subsequent queries.

### Command Syntax

```text
%img image_path [options]
```

### Command Options

| Option                  | Description                                                       |
| ----------------------- | ----------------------------------------------------------------- |
| `image_path`            | Path to the image file to process                                 |
| `-r`, `--resize WIDTH`  | Width to resize the image to (maintains aspect ratio)             |
| `-q`, `--quality VALUE` | Quality for lossy image formats (0.0-1.0)                         |
| `--show`                | Display the image inline after processing                         |
| `-i`, `--info`          | Display information about the image                               |
| `-a`, `--add-to-chat`   | Add the image to the current chat session (default: always added) |
| `-c`, `--convert`       | Force conversion to a compatible format                           |
| `-f`, `--format FORMAT` | Format to convert the image to (e.g., "jpg", "png", "webp")       |

### Examples

#### Display an Image with Information

```text
%img path/to/image.jpg --show --info
```

This command will display the image inline and show detailed metadata including dimensions, format, and file size.

#### Resize and Convert an Image

```text
%img path/to/image.png --resize 800 --format webp --quality 0.85 --show
```

This resizes the image to 800px width (maintaining aspect ratio), converts it to WebP format with 85% quality, and displays it in the notebook.

#### Add Multiple Images to Context

```text
%img image1.jpg
%img image2.png --resize 1024
%img image3.webp --info

# Now ask the LLM about the images
%%llm
Compare the three images I just shared. What are the key differences?
```

## How It Works

The `%img` magic command is powered by the `ImageProcessor` class from `cellmage.integrations.image_utils`. When you process an image:

1. The image is loaded using Pillow (PIL)
2. It's optionally resized and/or converted to a compatible format
3. Basic metadata is extracted and can be displayed
4. The processed image is encoded in base64 format
5. The image is added to your conversation history/context for LLM analysis
6. If requested with `--show`, it's displayed inline in the notebook

## Implementation Details

- The `ImageMagics` class in `cellmage/integrations/image_magic.py` implements the IPython magic command
- The `ImageProcessor` class in `cellmage/utils/image_utils.py` handles the image processing
- Format conversion prioritizes LLM-compatible formats
- Configuration settings are used for default values

### `ImageMagics` Class Architecture

The `ImageMagics` class extends `BaseMagics` and provides:

```python
@magics_class
class ImageMagics(BaseMagics):
    """IPython magic commands for displaying and processing images."""

    def __init__(self, shell):
        super().__init__(shell)
        self._image_processor = get_image_processor() if is_image_processing_available() else None

    @magic_arguments()
    @argument(...)  # Arguments definition
    @line_magic
    def img(self, line):
        """Process an image for LLM context and optionally display it."""
        # Implementation
```

### Error Handling

The implementation includes robust error handling for various scenarios:

```python
try:
    # Image processing logic
except Exception as e:
    logger.error(f"Error processing image: {str(e)}", exc_info=True)
    return f"Error processing image: {str(e)}"
```

### Integration with Chat Manager

When an image is processed, it's automatically added to the conversation context:

```python
chat_manager = self._get_chat_manager()
if chat_manager and hasattr(chat_manager, "conversation_manager"):
    llm_image = format_image_for_llm(image_data, mime_type, metadata)
    msg = Message(
        role="user",
        content="[Image sent]",
        metadata={"source": image_path, "llm_image": llm_image, **metadata},
    )
    chat_manager.conversation_manager.add_message(msg)
```

## Customizing Image Processing

### Configuration Settings

Image processing behavior can be customized through settings in `cellmage.config`:

- `image_default_width`: Default width to resize images to
- `image_default_quality`: Default quality for lossy formats (0.0-1.0)
- `image_target_format`: Default format for conversion
- `image_formats_llm_compatible`: List of formats compatible with LLMs

You can override these settings in your CellMage configuration.

### Extending the Integration

To extend or customize image processing:

1. **Subclass `ImageProcessor`**: Create a custom processor with additional capabilities

```python
from cellmage.integrations.image_utils import ImageProcessor

class MyCustomImageProcessor(ImageProcessor):
    def process_image(self, image_path, **kwargs):
        # Custom preprocessing
        # ...
        return super().process_image(image_path, **kwargs)
```

2. **Register a custom processor factory**:

```python
# Replace the default processor with your custom one
import cellmage.integrations.image_utils as utils

original_get_processor = utils.get_image_processor

def custom_get_processor():
    return MyCustomImageProcessor()

utils.get_image_processor = custom_get_processor
```

## Advanced Usage Examples

### Multiple Image Analysis

```text
# Process and add three images to context
%img image1.jpg --resize 800
%img image2.jpg --resize 800
%img image3.jpg --resize 800

# Ask the LLM to compare the images
%%llm
Compare the three images I sent. What are their similarities and differences?
```

### Working with Scientific Images

```text
# Process and analyze a microscopy image
%img microscopy_sample.tiff --convert --format png --show --info

%%llm
Describe the cellular structures visible in this microscopy image.
What abnormalities, if any, do you notice?
```

### Image Processing Workflow

```text
# Process a chart and ask for analysis
%img sales_chart.png --resize 1200 --show

%%llm
Analyze this sales chart. What are the key trends?
Can you identify seasonal patterns?
What recommendations would you make based on this data?
```

## Performance Considerations

- **Image Size**: Larger images require more memory and processing time
- **Format Conversion**: Converting between formats adds processing overhead
- **LLM Token Usage**: Images consume tokens from your LLM quota
- **Quality vs. Size**: Higher quality settings increase file size

## Best Practices

- Resize large images for better performance
- Use WebP format for best quality/size ratio
- Add the `--info` flag to see details about the original and processed images
- Always verify the image has been added to context by checking the confirmation message
- For better LLM analysis, ensure images are clear and focused on the relevant subject
- When analyzing multiple images, use consistent sizing for fair comparison

## Troubleshooting

Common issues and their solutions:

1. **"Image processing not available"**: Install Pillow with `pip install pillow`
2. **Image not found**: Check the file path and ensure it's accessible
3. **Format not recognized**: Try converting the image to a standard format like PNG or JPEG
4. **Large images**: Use the `--resize` option to reduce memory usage and improve LLM processing
