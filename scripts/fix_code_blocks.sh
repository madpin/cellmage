#!/usr/bin/env bash
# Script to identify and fix code blocks in Markdown files that contain special characters
# Changes language specifier from python to ipython for blocks with magic commands

set -e

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}Scanning for problematic code blocks in Markdown files${NC}"
echo -e "${BLUE}======================================================${NC}\n"

# Main directories to search (adjust as needed)
SEARCH_DIRS="docs/source"

# Counters
TOTAL_FILES=0
FIXED_FILES=0
PROBLEMATIC_BLOCKS=0
DEBUG_MODE=false

# Function to process a single file
process_file() {
    local file="$1"
    local temp_file=$(mktemp)
    local debug_file=$(mktemp)
    local file_modified=false
    local blocks_in_file=0

    echo -e "Checking ${YELLOW}$file${NC}..."

    # Start with the content of the original file
    cat "$file" > "$temp_file"

    # Use a more reliable approach with unique markers to avoid breaking code blocks
    # Step 1: Mark all code blocks with unique identifiers
    perl -i -p0e '
        # Give all markdown code blocks unique identifiers
        s/(```)(python|ipython|bash|sh|shell|text|ini|markdown|yaml|json)(\n.*?)(```)/CODEBLOCK_START_\2\3CODEBLOCK_END/gs;
    ' "$temp_file"

    # Copy temp file for debugging if needed
    if [ "$DEBUG_MODE" = true ]; then
        cp "$temp_file" "$debug_file.step1"
    fi

    # Step 2: Identify which Python blocks should be IPython based on their content
    perl -i -p0e '
        # Cell magic patterns (%%llm, %%bash, etc.)
        s/(CODEBLOCK_START_python)(\n.*?%%.+?.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

        # Line magic patterns (%llm, %load_ext, etc.)
        s/(CODEBLOCK_START_python)(\n.*?%[a-zA-Z][a-zA-Z0-9_]*.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

        # Blocks with --snippet pattern (very common in CellMage)
        s/(CODEBLOCK_START_python)(\n.*?--snippet.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

        # Question marks (common in IPython expressions)
        s/(CODEBLOCK_START_python)(\n.*?\?.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

        # Exclamation marks for shell commands
        s/(CODEBLOCK_START_python)(\n.*?!.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

        # Dollar signs in numerical contexts
        s/(CODEBLOCK_START_python)(\n.*?\$[0-9]+.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

        # IPython display functions
        s/(CODEBLOCK_START_python)(\n.*?display\s*\(.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

        # IPython-specific imports
        s/(CODEBLOCK_START_python)(\n.*?(?:import|from)\s+IPython.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

        # Common IPython patterns (load_ext)
        s/(CODEBLOCK_START_python)(\n.*?load_ext.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

        # LLM-specific patterns for CellMage
        s/(CODEBLOCK_START_python)(\n.*?llm(?:_config)?.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

        # Specific CellMage functions we know should be in IPython
        s/(CODEBLOCK_START_python)(\n.*?(?:%github|%gitlab|%jira|%confluence|%sqlite).*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;
    ' "$temp_file"

    # Copy temp file for debugging if needed
    if [ "$DEBUG_MODE" = true ]; then
        cp "$temp_file" "$debug_file.step2"
    fi

    # Step 3: Convert back to markdown format
    perl -i -p0e '
        # Convert all code blocks back to markdown format
        s/CODEBLOCK_START_([a-zA-Z]+)(.*?)CODEBLOCK_END/```\1\2```/gs;
    ' "$temp_file"

    # Copy temp file for debugging if needed
    if [ "$DEBUG_MODE" = true ]; then
        cp "$temp_file" "$debug_file.step3"
    fi

    # Step 4: Final safety pass - catch any remaining cases that might have been missed
    perl -i -p0e '
        # Last check for any Python blocks with magic commands
        s/(```)(python)(\n.*?%.*?)(```)/\1ipython\3\4/gs;
        s/(```)(python)(\n.*?%%.*?)(```)/\1ipython\3\4/gs;
        s/(```)(python)(\n.*?--snippet.*?)(```)/\1ipython\3\4/gs;
        s/(```)(python)(\n.*?llm.*?)(```)/\1ipython\3\4/gs;
    ' "$temp_file"

    # Check if the file was modified
    if ! cmp -s "$file" "$temp_file"; then
        file_modified=true

        # Count the number of blocks changed
        blocks_in_file=$(diff "$file" "$temp_file" | grep -c '< ```python' || true)

        # Apply the changes
        cp "$temp_file" "$file"
        echo -e "  ${GREEN}✓ Fixed $blocks_in_file code blocks${NC}"

        return $blocks_in_file
    else
        echo -e "  ${GREEN}✓ No issues found${NC}"
        return 0
    fi
}

# Function to test a specific file (useful for debugging)
test_specific_file() {
    local file="$1"

    if [ ! -f "$file" ]; then
        echo -e "${RED}Error: File '$file' not found${NC}"
        exit 1
    fi

    echo -e "${BLUE}Testing fix on specific file: $file${NC}"
    DEBUG_MODE=true
    process_file "$file"
    return $?
}

# Parse command line arguments
if [ "$1" = "--file" ] && [ -n "$2" ]; then
    # Test a specific file
    test_specific_file "$2"
    exit 0
fi

# Find all markdown files in the specified directories
MD_FILES=$(find $SEARCH_DIRS -name "*.md")

# Process each file
for file in $MD_FILES; do
    TOTAL_FILES=$((TOTAL_FILES + 1))

    # Process the file and capture the return value (number of blocks changed)
    process_file "$file"
    blocks_changed=$?

    # If blocks were changed, update our counters
    if [ $blocks_changed -gt 0 ]; then
        FIXED_FILES=$((FIXED_FILES + 1))
        PROBLEMATIC_BLOCKS=$((PROBLEMATIC_BLOCKS + blocks_changed))
    fi
done

echo -e "\n${BLUE}===========================${NC}"
echo -e "${BLUE}Scan Complete${NC}"
echo -e "${BLUE}===========================${NC}"
echo -e "Total Markdown files scanned: ${YELLOW}$TOTAL_FILES${NC}"
echo -e "Files with fixed code blocks: ${GREEN}$FIXED_FILES${NC}"
echo -e "Total code blocks fixed: ${GREEN}$PROBLEMATIC_BLOCKS${NC}"
echo ""
echo -e "Fix summary:"
echo -e "  - Changed python → ipython for blocks with:"
echo -e "    * Line and cell magic commands (% and %%)"
echo -e "    * CellMage command parameters (--snippet, etc.)"
echo -e "    * Question marks (?) in expressions"
echo -e "    * Exclamation marks (!) for shell commands"
echo -e "    * Dollar signs ($) in numerical contexts"
echo -e "    * IPython-specific imports and functions"
echo -e "    * Any mention of 'llm' (including %%llm and %llm_config)"
echo -e "  - Using a marker-based approach to avoid breaking markdown"
echo -e "  - Bash/shell code blocks were NOT modified"

# Make the script executable
chmod +x "$0"
