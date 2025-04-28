import datetime
import os
from typing import Any, List, Optional

from IPython.display import Markdown, display


def display_files_as_table(
    files_list: List[str],
    directory: str,
    columns: int = 3,
    show_modified_date: bool = False,
    show_size: bool = False,
    show_lines: bool = False,
) -> str:
    """
    Format a list of files as a markdown table with customizable columns.

    Args:
        files_list: List of filenames to display
        directory: Path to the directory containing the files
        columns: Number of columns to display
        show_modified_date: Whether to show last modified date
        show_size: Whether to show file size in KB
        show_lines: Whether to show line count

    Returns:
        A markdown-formatted table as a string
    """
    # Sort files alphabetically for better readability
    files_list = sorted(files_list)

    # Determine what columns to show
    headers = ["Filename"]
    if show_modified_date:
        headers.append("Last Modified")
    if show_size:
        headers.append("Size (KB)")
    if show_lines:
        headers.append("Lines")

    # Create markdown table header
    table = ["| " + " | ".join(headers) + " |"]
    table.append("| " + " | ".join(["---" for _ in range(len(headers))]) + " |")

    # Process each file
    for filename in files_list:
        file_path = os.path.join(directory, filename)
        if not os.path.isfile(file_path):
            continue

        row_data = [filename]

        # Get last modified date if requested
        if show_modified_date:
            mod_time = os.path.getmtime(file_path)
            mod_date = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
            row_data.append(mod_date)

        # Get file size if requested
        if show_size:
            size_kb = round(os.path.getsize(file_path) / 1024, 2)
            row_data.append(f"{size_kb}")

        # Count lines if requested
        if show_lines:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    line_count = sum(1 for _ in f)
                row_data.append(str(line_count))
            except Exception:
                row_data.append("N/A")

        table.append("| " + " | ".join(row_data) + " |")

    return "\n".join(table)


def display_files_paginated(
    files_list: List[str],
    directory: str,
    page_size: int = 10,
    page: int = 1,
    **kwargs: Any,
) -> str:
    """
    Display files with pagination as a markdown table.

    Args:
        files_list: List of filenames to display
        directory: Path to the directory containing the files
        page_size: Number of files per page (0 to show all files)
        page: Current page number (1-based)
        **kwargs: Additional arguments to pass to display_files_as_table

    Returns:
        A markdown-formatted string with table and pagination info
    """
    # If page_size is 0, show all files
    if page_size == 0:
        page_size = len(files_list)

    total_pages = (len(files_list) + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, len(files_list))

    page_files = files_list[start_idx:end_idx]
    md_table = display_files_as_table(page_files, directory, **kwargs)

    pagination_info = f"Page {page} of {total_pages} | Total files: {len(files_list)}"
    return f"### Files in Directory\n{md_table}\n\n{pagination_info}"


def list_directory_files(
    directory_path: str,
    extensions: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    include_hidden: bool = False,
) -> List[str]:
    """
    List files in a directory with filtering options.

    Args:
        directory_path: Path to the directory
        extensions: List of file extensions to include (e.g., ['.py', '.md'])
        exclude_patterns: List of patterns to exclude
        include_hidden: Whether to include hidden files (starting with .)

    Returns:
        List of filenames that match the criteria
    """
    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        return []

    files = os.listdir(directory_path)
    result = []

    for filename in files:
        # Skip directories
        if os.path.isdir(os.path.join(directory_path, filename)):
            continue

        # Skip hidden files if not included
        if not include_hidden and filename.startswith("."):
            continue

        # Filter by extension
        if extensions:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in extensions and ext not in [e.lower() for e in extensions]:
                continue

        # Exclude specific patterns
        if exclude_patterns:
            if any(pattern in filename for pattern in exclude_patterns):
                continue

        result.append(filename)

    return result


def display_directory(
    directory_path: str,
    page_size: int = 0,
    page: int = 1,
    extensions: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    include_hidden: bool = False,
    show_modified_date: bool = True,
    show_size: bool = True,
    show_lines: bool = True,
) -> None:
    """
    Display files from a directory with various options and render directly in Jupyter.

    This is a convenience function that combines listing files and displaying them.

    Args:
        directory_path: Path to the directory to display
        page_size: Number of files per page (0 to show all files)
        page: Current page number (1-based)
        extensions: List of file extensions to include (e.g., ['.py', '.md'])
        exclude_patterns: List of patterns to exclude
        include_hidden: Whether to include hidden files (starting with .)
        show_modified_date: Whether to show last modified date
        show_size: Whether to show file size
        show_lines: Whether to show line count
    """
    # Get the list of files
    files = list_directory_files(
        directory_path,
        extensions=extensions,
        exclude_patterns=exclude_patterns,
        include_hidden=include_hidden,
    )

    # Generate the markdown table
    markdown_content = display_files_paginated(
        files,
        directory_path,
        page_size=page_size,
        page=page,
        show_modified_date=show_modified_date,
        show_size=show_size,
        show_lines=show_lines,
    )

    # Display the markdown in Jupyter
    display(Markdown(markdown_content))
