# 🖼️ Image Integration

CellMage helps you work with images directly in your notebooks by providing the `%img` magic command, which processes images for optimal use with Large Language Models (LLMs). This integration allows you to display images inline, resize them, convert formats, and add them to the conversation context for visual analysis by LLMs.

## Using the Image Magic Command

The `%img` magic command provides a simple interface for image processing:

```ipython
%img path/to/image.jpg [options]
```

### Key Features

- **Automatic Format Conversion**: Converts images to LLM-compatible formats
- **Resizing**: Optimize images for better LLM processing
- **Quality Control**: Adjust compression levels for lossy formats
- **Metadata Display**: View image details including dimensions and format
- **LLM Context Integration**: Add images to your conversation history for visual analysis

### Command Options

| Option                | Description                                                       |
| --------------------- | ----------------------------------------------------------------- |
| `image_path`          | Path to the image file to process                                 |
| `-r, --resize WIDTH`  | Width to resize the image to (maintains aspect ratio)             |
| `-q, --quality VALUE` | Quality for lossy image formats (0.0-1.0)                         |
| `--show`              | Display the image inline after processing                         |
| `-i, --info`          | Display information about the image                               |
| `-a, --add-to-chat`   | Add the image to the current chat session (default: always added) |
| `-c, --convert`       | Force conversion to a compatible format                           |
| `-f, --format FORMAT` | Format to convert the image to (e.g., "jpg", "png", "webp")       |

### Examples

#### Basic Usage: Add Image to Context

Simply process an image and add it to the LLM context without displaying it:

```ipython
%img path/to/your/image.jpg
# Output: ✅ image.jpg processed and added to conversation history.
```

#### Display Image with Information

Process the image, display it inline, and show detailed metadata:

```ipython
%img path/to/your/image.jpg --show --info
# Displays the image and shows metadata like dimensions, format, and file size
```

#### Resize and Convert

Resize an image to a specific width and convert it to a different format:

```ipython
%img path/to/your/image.png --resize 800 --format webp --quality 0.85 --show
# Resizes to 800px width, converts to WebP format with 85% quality, and displays
```

## Image Processing Utilities

Under the hood, CellMage's image integration uses utility functions from `cellmage.integrations.image_utils` module, which provides:

- **Format Detection**: Automatically identify image formats
- **Format Conversion**: Convert between different image formats
- **Resizing**: Intelligently resize images while maintaining aspect ratios
- **Base64 Encoding**: Encode images for API compatibility
- **Metadata Extraction**: Get detailed information about images

For more details about the image utilities, see [Image Utilities](utils/image_utils.md).

### Requirements

Image processing requires the Pillow library:

```bash
pip install pillow
```

## Technical Implementation

The image magic integration consists of two main components:

1. **`ImageMagics` Class**: Defined in `cellmage.magic_commands.tools.image_magic`, this implements the IPython magic command and handles user interaction.
2. **`ImageProcessor` Class**: Found in `cellmage.integrations.image_utils`, this handles the core image processing tasks.

For details about the technical implementation of the image magic integration, see the [Image Magic Integration](integrations/image_magic_integration.md) page.

## Using Images with LLMs

When you process an image with the `%img` command, it is automatically:

1. Processed for optimal size and format
2. Added to your conversation history
3. Included in the context for future LLM queries

This allows the LLM to "see" and analyze the image in subsequent interactions, enabling visual analysis, description, and question-answering about image content.

### Example Workflow

```ipython
# First, process and add an image to context
%img path/to/chart.png --resize 1024 --show

# Now ask the LLM about the image
%%llm
What trends can you identify in this chart? What might explain the spike in February?
```

## Configuration

Image processing behavior can be customized through CellMage's configuration options:

- `image_default_width`: Default width for image resizing (if not specified)
- `image_default_quality`: Default quality setting for lossy formats (0.0-1.0)
- `image_target_format`: Default format for conversion when needed
- `image_formats_llm_compatible`: List of formats considered compatible with LLMs

These settings can be adjusted in your `.env` file or through environment variables.
