# CellMage Extension Overview

## Functionality

CellMage provides a set of IPython/Jupyter extensions for enhanced interaction with LLMs and various services.

When you load the extension with `%load_ext cellmage`, it initializes:

1. **Core Magic Commands**:
   - `%llm` / `%cellm` - For LLM interactions
   - `%config` - For configuring CellMage settings
   - `%ambient` - For toggling ambient mode

2. **Tool Magic Commands**:
   - `%jira` - Interact with Jira issues and boards
   - `%confluence` - Access and update Confluence pages
   - `%github` - Query GitHub repositories and issues
   - `%gitlab` - Work with GitLab projects and issues
   - `%gdocs` - Read from and write to Google Docs
   - `%img` / `%image` - Generate and manipulate images
   - `%webcontent` - Extract content from web pages
   - `%sqlite` - Execute SQL queries against SQLite databases

3. **Integration Utilities**:
   - Support libraries for each tool magic
   - Helper functions for API interactions

## Testing the Extension

To test the CellMage extension in IPython or Jupyter:

1. Load the extension:
   ```python
   %load_ext cellmage
   ```

2. Check available extensions and tools:
   ```python
   # Run the test script
   %run test_extension.py
   ```

3. Run diagnostics to check component status:
   ```bash
   python diagnostics.py
   ```

## Troubleshooting

If the extension doesn't load properly:

1. Check that all requirements are installed
2. Run the diagnostics script to identify component issues
3. Verify that there are no conflicting IPython extensions

## Design Notes

- The extension uses a modular design with dynamic discovery of tools and integrations
- Core functionality is in the main CellMage module
- Tool-specific magic commands are in `cellmage/magic_commands/tools/`
- Integration utilities are in `cellmage/integrations/`
