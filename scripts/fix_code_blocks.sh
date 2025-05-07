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

# Use the full docs/source tree to capture all markdown files recursively
DOCS_DIR="docs/source"

# Counters
TOTAL_FILES=0
FIXED_FILES=0
PROBLEMATIC_BLOCKS=0
DEBUG_MODE=false
MAX_ITERATIONS=3  # Maximum number of passes to ensure we catch everything
ERRORS=0

# Function to process a single file
process_file() {
    local file="$1"
    local temp_file=$(mktemp)
    local debug_file=$(mktemp)
    local file_modified=false
    local blocks_in_file=0
    local iteration=0
    local changes_made=true

    echo -e "Checking ${YELLOW}$file${NC}..."

    # Use a trap to ensure temp files are cleaned up even if there's an error
    # Properly escape the glob pattern to avoid unintended file removal
    trap 'rm -f "$temp_file"; rm -f "${debug_file}"*' EXIT

    # Start with the content of the original file
    cat "$file" > "$temp_file" || {
        echo -e "  ${RED}✗ Failed to read file${NC}"
        return 0
    }

    # Keep making passes until no more changes or max iterations reached
    while [ "$changes_made" = true ] && [ $iteration -lt $MAX_ITERATIONS ]; do
        iteration=$((iteration + 1))
        changes_made=false

        local temp_file_before=$(mktemp)
        cp "$temp_file" "$temp_file_before"

        # Full transformation process with error handling
        # Step 1: Mark all code blocks with unique identifiers
        perl -i -p0e '
            # Give all markdown code blocks unique identifiers
            s/(```)(python|ipython|bash|sh|shell|text|ini|markdown|yaml|json)(\n.*?)(```)/CODEBLOCK_START_\2\3CODEBLOCK_END/gs;
        ' "$temp_file" || {
            echo -e "  ${RED}✗ Error in step 1 processing${NC}"
            rm -f "$temp_file_before"
            return 0
        }

        # Copy temp file for debugging if needed
        if [ "$DEBUG_MODE" = true ]; then
            cp "$temp_file" "${debug_file}.step1.iter${iteration}"
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

            # Dollar signs in any context
            s/(CODEBLOCK_START_python)(\n.*?\$.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

            # IPython display functions
            s/(CODEBLOCK_START_python)(\n.*?display\s*\(.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

            # IPython-specific imports
            s/(CODEBLOCK_START_python)(\n.*?(?:import|from)\s+IPython.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

            # Common IPython patterns (load_ext)
            s/(CODEBLOCK_START_python)(\n.*?load_ext.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

            # LLM-specific patterns for CellMage - more precise pattern to avoid matching "cellmage"
            s/(CODEBLOCK_START_python)(\n.*?(?:\%|%%|\s+)llm(?:_config)?.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

            # Specific CellMage functions we know should be in IPython
            s/(CODEBLOCK_START_python)(\n.*?(?:%github|%gitlab|%jira|%confluence|%sqlite).*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

            # Triple backticks inside code blocks
            s/(CODEBLOCK_START_python)(\n.*?```.*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;

            # Special mathematical Unicode characters
            s/(CODEBLOCK_START_python)(\n.*?[²³π].*?)CODEBLOCK_END/CODEBLOCK_START_ipython\2CODEBLOCK_END/gs;
        ' "$temp_file" || {
            echo -e "  ${RED}✗ Error in step 2 processing${NC}"
            rm -f "$temp_file_before"
            return 0
        }

        # Copy temp file for debugging if needed
        if [ "$DEBUG_MODE" = true ]; then
            cp "$temp_file" "${debug_file}.step2.iter${iteration}"
        fi

        # Step 3: Convert back to markdown format
        perl -i -p0e '
            # Convert all code blocks back to markdown format
            s/CODEBLOCK_START_([a-zA-Z]+)(.*?)CODEBLOCK_END/```\1\2```/gs;
        ' "$temp_file" || {
            echo -e "  ${RED}✗ Error in step 3 processing${NC}"
            rm -f "$temp_file_before"
            return 0
        }

        # Copy temp file for debugging if needed
        if [ "$DEBUG_MODE" = true ]; then
            cp "$temp_file" "${debug_file}.step3.iter${iteration}"
        fi

        # Step 4: More aggressive final pass to catch any that might have been missed
        perl -i -p0e '
            # Last check for any Python blocks with magic commands or special characters
            s/(```)(python)(\n.*?%.*?)(```)/\1ipython\3\4/gs;
            s/(```)(python)(\n.*?%%.*?)(```)/\1ipython\3\4/gs;
            s/(```)(python)(\n.*?--snippet.*?)(```)/\1ipython\3\4/gs;

            # More precise LLM pattern for the last check
            s/(```)(python)(\n.*?(?:\%|%%|\s+)llm.*?)(```)/\1ipython\3\4/gs;

            s/(```)(python)(\n.*?\?.*?)(```)/\1ipython\3\4/gs;
            s/(```)(python)(\n.*?\$.*?)(```)/\1ipython\3\4/gs;
            s/(```)(python)(\n.*?!.*?)(```)/\1ipython\3\4/gs;
            s/(```)(python)(\n.*?```.*?)(```)/\1ipython\3\4/gs;
            s/(```)(python)(\n.*?[²³π].*?)(```)/\1ipython\3\4/gs;
        ' "$temp_file" || {
            echo -e "  ${RED}✗ Error in step 4 processing${NC}"
            rm -f "$temp_file_before"
            return 0
        }

        # Check if this iteration made any changes
        if ! cmp -s "$temp_file_before" "$temp_file"; then
            changes_made=true
            if [ "$DEBUG_MODE" = true ]; then
                echo "  Changes detected in iteration $iteration"
            fi
        fi

        rm -f "$temp_file_before"
    done

    # Check if the final file was modified compared to the original
    if ! cmp -s "$file" "$temp_file"; then
        file_modified=true

        # Count the number of blocks changed
        blocks_in_file=$(diff "$file" "$temp_file" | grep -c '< ```python' || true)

        if [ $blocks_in_file -gt 0 ]; then
            # Apply the changes
            cp "$temp_file" "$file" || {
                echo -e "  ${RED}✗ Failed to write changes to file${NC}"
                ERRORS=$((ERRORS + 1))
                return 0
            }
            echo -e "  ${GREEN}✓ Fixed $blocks_in_file code blocks in $iteration iterations${NC}"
        else
            # There were other changes but not specifically ```python blocks
            # This can happen with nested fixes
            cp "$temp_file" "$file" || {
                echo -e "  ${RED}✗ Failed to write changes to file${NC}"
                ERRORS=$((ERRORS + 1))
                return 0
            }
            echo -e "  ${GREEN}✓ Fixed code blocks (structure changes)${NC}"
            blocks_in_file=1  # Just count it as at least one change
        fi

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

# Make sure we find all markdown files upfront
echo -e "${BLUE}Finding all Markdown files in $DOCS_DIR...${NC}"
MD_FILES=$(find "$DOCS_DIR" -type f -name "*.md" | sort)
FILE_COUNT=$(echo "$MD_FILES" | wc -l | xargs)
echo -e "${GREEN}Found $FILE_COUNT Markdown files to process${NC}"

# Keep track of progress
CURRENT_FILE=0

# Process each file with proper error handling
for file in $MD_FILES; do
    TOTAL_FILES=$((TOTAL_FILES + 1))
    CURRENT_FILE=$((CURRENT_FILE + 1))

    # Show progress indicator
    echo -e "${BLUE}[$CURRENT_FILE/$FILE_COUNT]${NC} Processing file: $file"

    # Process the file and capture the return value (number of blocks changed)
    set +e  # Don't exit on error
    process_file "$file"
    blocks_changed=$?
    set -e  # Resume exit on error

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
if [ $ERRORS -gt 0 ]; then
    echo -e "Errors encountered: ${RED}$ERRORS${NC}"
fi
echo ""
echo -e "Fix summary:"
echo -e "  - Changed python → ipython for blocks with:"
echo -e "    * Line and cell magic commands (% and %%)"
echo -e "    * CellMage command parameters (--snippet, etc.)"
echo -e "    * Question marks (?) in expressions"
echo -e "    * Exclamation marks (!) for shell commands"
echo -e "    * Dollar signs (\$) in any context"
echo -e "    * Triple backticks inside code blocks"
echo -e "    * Special mathematical characters like ² or π"
echo -e "    * IPython-specific imports and functions"
echo -e "    * Any mention of '%llm' or '%%llm' (not words containing 'llm')"
echo -e "  - Using a marker-based approach to avoid breaking markdown"
echo -e "  - Processing files with multiple iterations to ensure all patterns are caught"
echo -e "  - Bash/shell code blocks were NOT modified"

# Make the script executable
chmod +x "$0"
