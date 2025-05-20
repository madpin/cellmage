# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [v0.9.7](https://github.com/madpin/cellmage/releases/tag/v0.9.7) - 2025-05-20

### Added
- Implemented token counting utilities and refactored related handlers to improve token management.
- Added base directory configuration support for working files, including updates to the related documentation.

### Changed
- Replaced `history_manager` with `conversation_manager` across the codebase to unify conversation handling.
- Removed obsolete GitLab magic command tests as part of test suite cleanup.

### Added
- Added integration tests for GitLab magic command functionality to ensure robust feature coverage.


## [v0.9.6](https://github.com/madpin/cellmage/releases/tag/v0.9.6) - 2025-05-19

### Added
- Added support for base directory configuration for working files, enhancing flexibility in file management. Updated related documentation to reflect this new feature.
- Added integration tests for GitLab magic command functionality to improve test coverage and reliability.

### Changed
- Removed obsolete GitLab magic command tests as part of test suite refactoring to maintain codebase relevance and cleanliness.


## [v0.9.5](https://github.com/madpin/cellmage/releases/tag/v0.9.5) - 2025-05-13

### Changed
- Improved the documentation build process by updating the Makefile.
- Cleaned up the documentation index by removing unused integrations and magic commands.


## [v0.9.4](https://github.com/madpin/cellmage/releases/tag/v0.9.4) - 2025-05-13

## [v0.9.2](https://github.com/madpin/cellmage/releases/tag/v0.9.2) - 2025-05-13

## [v0.9.1](https://github.com/madpin/cellmage/releases/tag/v0.9.1) - 2025-05-11
### Fixed
- Improved changelog generation by handling cases where the current tag does not exist and ensuring the version is updated before generating the changelog.

## [v0.9.0](https://github.com/madpin/cellmage/releases/tag/v0.9.0) - 2025-05-11
### Changed
- Refactored the release script to improve the version bumping process and automate changelog generation.

## [v0.8.3](https://github.com/madpin/cellmage/releases/tag/v0.8.3) - 2025-05-11
### Added
- Implemented dynamic loading for integrations and magic commands to enhance plugin discovery.
- Added image processing capabilities through new IPython magic commands, including the `%img` magic command, along with related utilities and improved documentation.

### Changed
- Refactored history management to utilize the `ConversationManager` for better structure and maintainability.
- Reorganized and improved the testing framework for CellMage, enhancing test coverage and organization.
- Enhanced overall functionality and performance through various code improvements.
- Added a table of contents to the utilities documentation for easier navigation.

### Fixed
- Corrected `sed` commands in the release script to ensure consistent version incrementing.

### Removed
- Removed references to the deprecated `history_manager` module from the API documentation.
- Eliminated obsolete integration tests and added `black` as a development dependency for code formatting.

## [v0.8.2](https://github.com/madpin/cellmage/releases/tag/v0.8.2) - 2025-05-08
### Added
- Added a comprehensive magic command cheatsheet for CellMage to improve user accessibility and reference.
- Enhanced Google Docs integration by introducing timeout and parallel fetch settings, along with token counting features in history and status displays.
- Updated API documentation and improved Sphinx configuration by incorporating the autosummary extension for better documentation generation.

### Changed
- Refactored the ambient mode and magic command architecture to improve code structure and maintainability.
- Refactored documentation and removed obsolete test files to streamline the codebase and documentation quality.

## [v0.8.1](https://github.com/madpin/cellmage/releases/tag/v0.8.1) - 2025-05-08
### Added
- Enhanced Google Docs integration by adding search and content retrieval features, improving the ability to interact with and extract information from Google Docs.

## [v0.8.0](https://github.com/madpin/cellmage/releases/tag/v0.8.0) - 2025-05-08
### Added
- Added integration with Google Docs to enable fetching and processing of document content.

## [v0.7.0](https://github.com/madpin/cellmage/releases/tag/v0.7.0) - 2025-05-08
### Added
- Introduced WebContent integration to enable fetching and processing of website content, enhancing data retrieval capabilities.

## [v0.6.0](https://github.com/madpin/cellmage/releases/tag/v0.6.0) - 2025-05-07
### Added
- Added comprehensive tutorials covering Jira integration, a quickstart guide, streaming responses, token usage, snippets, and custom personas to enhance user onboarding and feature understanding.

### Changed
- Changed code block language specifiers from `python` to `ipython` in documentation and tutorials for improved clarity.
- Enhanced Sphinx compatibility by explicitly defining `__annotations__` in the `Settings` class.

### Fixed
- Fixed missing help description for the `--param` argument in the `llm` magic command.
- Updated Sphinx build options and suppressed additional warnings to improve documentation build quality.
- Added missing newline in the docstring for the `llm_magic` function.
- Improved code block processing in Markdown files to increase accuracy and correctly handle multiple iterations.

## [v0.5.15](https://github.com/madpin/cellmage/releases/tag/v0.5.15) - 2025-05-07
### Fixed
- Corrected the code block syntax in the documentation from Python to plain text to improve clarity.

## [v0.5.14](https://github.com/madpin/cellmage/releases/tag/v0.5.14) - 2025-05-07
### Added
- Enhanced the documentation by introducing magical themes and improving the overall structure across multiple files.

## [v0.5.13](https://github.com/madpin/cellmage/releases/tag/v0.5.13) - 2025-05-07
### Changed
- Improved model handling in the changelog generation script to enhance release management.

### Fixed
- Commented out the formats section in the ReadTheDocs configuration to resolve PDF and EPUB build failures.

## [v0.5.12](https://github.com/madpin/cellmage/releases/tag/v0.5.12) - 2025-05-07
### Added
- Re-enabled PDF and EPUB formats in the ReadTheDocs configuration, including support for LaTeX emojis.

## [v0.5.11](https://github.com/madpin/cellmage/releases/tag/v0.5.11) - 2025-05-07
### Fixed
- Commented out the formats section in the ReadTheDocs configuration to resolve PDF and EPUB build failures.

## [v0.5.10](https://github.com/madpin/cellmage/releases/tag/v0.5.10) - 2025-05-07
### Added
- Added documentation dependencies for Sphinx and related tools to improve project documentation.

## [v0.5.9](https://github.com/madpin/cellmage/releases/tag/v0.5.9) - 2025-05-07
### Added
- Enhanced the changelog generation functionality to support multiple large language models (LLM). Updated the documentation to reflect these improvements.

## [v0.5.8](https://github.com/madpin/cellmage/releases/tag/v0.5.8) - 2025-05-07
### Changed
- Updated the default large language model (LLM) to gpt-4.1-mini to improve overall performance.

## [v0.5.7](https://github.com/madpin/cellmage/releases/tag/v0.5.7) - 2025-05-07
### Added
- Added build configuration for Ubuntu 22.04 and Python 3.9 in the Read the Docs YAML file to support updated documentation builds.

## [v0.5.6](https://github.com/madpin/cellmage/releases/tag/v0.5.6) - 2025-05-07
### Added
- Introduced LLM-powered changelog generation and added a corresponding target in the Makefile.
- Added pre-commit configuration and updated dependencies to improve code quality checks.
- Enhanced virtual environment setup by including optional dependencies and improving caching mechanisms.

### Changed
- Enhanced the release process by supporting minor and major version increments in both the Makefile and release script.
- Updated the release script to automatically update the version if the tag already exists.
- Updated model references to use gpt-4.1-nano and improved release scripts accordingly.
- Updated Python version requirements to 3.9 across all configuration files.
- Refactored version update logic in the release script to use separate `sed` commands for better clarity.

### Fixed
- Corrected pip install command syntax and updated requirements to ensure consistency.
- Updated the installation and virtual environment setup commands to include all optional dependencies.
- Cleaned up whitespace and formatting inconsistencies across multiple files.

## [v0.5.5](https://github.com/madpin/cellmage/releases/tag/v0.5.5) - 2025-05-06
### Added
- Implemented configuration handlers for the `%llm_config` magic command, enabling enhanced configuration management.
- Introduced the LLM magic command as part of a refactored magic commands architecture.

### Changed
- Refactored the magic commands architecture to improve modularity and maintainability.
- Improved logging and debug information across `ChatManager`, `HistoryManager`, and `ConfigMagics` for better traceability.
- Enhanced history management and logging within `ChatManager` and `HistoryManager`.
- Updated logging in GitHub, GitLab, and Jira magic commands to use `logger.debug` for more detailed debug output.
- Added `refactored_magic_architecture` to the Development section in the documentation (`index.md`).

### Removed
- Added `.data/conversations.db` to `.gitignore` to exclude conversation database files from version control.

## [v0.5.4](https://github.com/madpin/cellmage/releases/tag/v0.5.4) - 2025-05-04
### Changed
- Updated dependencies to use the latest Confluent platform integration for improved compatibility and performance.

## [v0.5.3](https://github.com/madpin/cellmage/releases/tag/v0.5.3) - 2025-05-04
### Changed
- Updated the Confluence integration documentation by changing code blocks to use text format for improved clarity.

## [v0.5.2](https://github.com/madpin/cellmage/releases/tag/v0.5.2) - 2025-05-04
### Changed
- Updated the code blocks in the Confluence integration documentation to use the `python-repl` format for improved clarity.

## [v0.5.1](https://github.com/madpin/cellmage/releases/tag/v0.5.1) - 2025-05-03
### Added
- Added Confluence integration with new magic commands and updated the related documentation.
- Introduced a placeholder for the LLM magic command in the GitHub integration.

### Changed
- Refactored IPython magic commands to use a base class for shared functionality, improving code maintainability.
- Changed code block syntax from Python to text for GitHub and SQLite magic command examples to enhance readability.
- Improved formatting of old_path assignment in GitHubUtils for better code clarity.

### Fixed
- Fixed formatting issues in log messages and print statements across multiple files to ensure consistent output.

## [v0.5.0](https://github.com/madpin/cellmage/releases/tag/v0.5.0) - 2025-05-03
### Added
- Introduced GitHub integration featuring a magic command and utility functions to enhance workflow automation.
- Implemented SQLite-based storage for conversation history, including advanced features such as tagging, statistics tracking, and raw API response storage. Documentation and example usage have been updated to support seamless integration.

## [v0.4.7](https://github.com/madpin/cellmage/releases/tag/v0.4.7) - 2025-05-01
### Added
- Enhanced token tracking in Jira Magic by counting tokens in ticket content and including this information in message metadata.

### Changed
- Improved session management by refining session listing output and error handling. The `session_id` is now consistently stored as a string in metadata.

## [v0.4.6](https://github.com/madpin/cellmage/releases/tag/v0.4.6) - 2025-05-01
### Changed
- Refactored the message deduplication logic in `ChatManager` to improve readability and enhanced it to retain the last occurrence of duplicate messages for both non-system and system messages.

### Fixed
- Corrected the token display direction in `IPythonContextProvider` to accurately indicate input and output tokens.

## [v0.4.5](https://github.com/madpin/cellmage/releases/tag/v0.4.5) - 2025-05-01
### Changed
- Improved persona handling in `ChatManager` and IPython magic commands, including the addition of detailed logging for persona requests and system message management.

## [v0.4.4](https://github.com/madpin/cellmage/releases/tag/v0.4.4) - 2025-05-01
### Changed
- Refactored snippet directory handling in `get_default_manager` to exclusively use the `llm_snippets` directory instead of `snippets`.
- Improved test readability in GitLab magic command tests by formatting environment variable patches.

## [v0.4.3](https://github.com/madpin/cellmage/releases/tag/v0.4.3) - 2025-05-01
### Added
- Added response content handling for status information in the IPython context provider and magic commands.

### Changed
- Refactored ChatManager and IPythonContextProvider to improve response handling.
- Enhanced GitLab magic command tests with better mocking and improved structure.
- Improved message deduplication in ChatManager to preserve system messages originating from different sources.
- Updated the author description in the README.md to reflect beverage preference.

## [v0.4.2](https://github.com/madpin/cellmage/releases/tag/v0.4.2) - 2025-04-29
### Added
- Added support for custom headers in LLM requests and updated configuration settings.

### Changed
- Refactored token counting in ChatManager and HistoryManager to improve accuracy.
- Enhanced persona and snippet output formatting in NotebookLLMMagics for better readability.
- Refactored header preparation in DirectLLMAdapter and LangChainAdapter to streamline request handling.
- Updated test fixtures, including renaming in `test_jira_magic.py` and improving IPython fixture reliability.
- Changed code block syntax from `python` to `ipython` for the LLM prompt example in the Jira integration documentation.

## [v0.4.1](https://github.com/madpin/cellmage/releases/tag/v0.4.1) - 2025-04-29
### Added
- No new features were added in this release.

### Changed
- No changes to existing functionality were made in this release.

### Fixed
- No bug fixes were included in this release.

### Removed
- No features were removed in this release.

### Security
- No security fixes were included in this release.

### Deprecated
- No features were deprecated in this release.

## [v0.4.0](https://github.com/madpin/cellmage/releases/tag/v0.4.0) - 2025-04-29
### Added
- No new features were introduced in this release.

### Changed
- No changes to existing functionality were made in this release.

### Fixed
- No bug fixes were included in this release.

### Removed
- No features were removed in this release.

### Security
- No security fixes were applied in this release.

### Deprecated
- No features were deprecated in this release.

## [v0.3.1](https://github.com/madpin/cellmage/releases/tag/v0.3.1) - 2025-04-29
### Changed
- Updated the code block syntax from Python to IPython in the Jira integration documentation to improve clarity in the LLM prompt example.

## [v0.3.0](https://github.com/madpin/cellmage/releases/tag/v0.3.0) - 2025-04-29
### Added
- Added support for custom headers in LLM requests, allowing more flexible configuration settings.

### Changed
- Refactored header preparation in DirectLLMAdapter and LangChainAdapter to improve code clarity and maintainability.
- Updated the IPython fixture to enhance reliability in tests.

## [v0.2.5](https://github.com/madpin/cellmage/releases/tag/v0.2.5) - 2025-04-29
### Added
- Introduced Jira integration featuring a magic command and utility functions to enhance task management capabilities.

### Changed
- Updated README and Jira integration documentation for improved clarity and more comprehensive usage examples.
- Refactored the Makefile and Jira integration tests to improve consistency and readability.
- Refined the epic link field assignment in JiraUtils and updated the documentation for the %%llm magic command.
- Corrected the author name in README.md to Thiago MadPin.

## [v0.2.4](https://github.com/madpin/cellmage/releases/tag/v0.2.4) - 2025-04-29
### Changed
- Updated GitHub Actions workflow to include permissions for write access, improving automation capabilities.

## [v0.2.3](https://github.com/madpin/cellmage/releases/tag/v0.2.3) - 2025-04-29
### Changed
- Refactored IPython display imports to improve code structure and readability.
- Simplified multi-line statements and enhanced logging messages across various modules for better maintainability.
- Updated linting and formatting configurations to improve overall code quality.

### Removed
- Removed unused import of `Javascript` from the IPython display module.

## [v0.2.2](https://github.com/madpin/cellmage/releases/tag/v0.2.2) - 2025-04-29
### Added
- Added UUID support to the IPython context provider to enhance context tracking capabilities.

### Changed
- Improved display handling in the IPython context provider for better user experience.
- Updated project metadata to ensure clarity and accuracy.

## [v0.2.1](https://github.com/madpin/cellmage/releases/tag/v0.2.1) - 2025-04-28
### Changed
- Refactored code to improve readability and consistency by simplifying multi-line statements and enhancing logging messages across various modules.

## [v0.2.0](https://github.com/madpin/cellmage/releases/tag/v0.2.0) - 2025-04-28
### Changed
- Updated the README.md to improve clarity and engagement by refining feature descriptions and installation instructions.
- Simplified the `get_default_manager` function by removing the version variable and streamlining error messages.

### Removed
- Deleted obsolete persona and documentation files including code writer, coder, non-technical documentation specialist, and example persona.
- Removed unused snippets related to EVO, example snippet, and personal details of Thiago.
- Cleared out empty Jupyter notebooks for markdown and model mappings demos.

## [v0.1.3](https://github.com/madpin/cellmage/releases/tag/v0.1.3) - 2025-04-28
### Added
- Initial release of version v0.1.3.

## [v0.1.2](https://github.com/madpin/cellmage/releases/tag/v0.1.2) - 2025-04-28
### Added
- No new features were added in this release.

### Changed
- No changes to existing functionality were made in this release.

### Fixed
- No bug fixes were included in this release.

### Removed
- No features were removed in this release.

### Security
- No security fixes were applied in this release.

### Deprecated
- No features were deprecated in this release.

## [v0.1.1](https://github.com/madpin/cellmage/releases/tag/v0.1.1) - 2025-04-28
### Added
- Introduced message deduplication in ChatManager and improved snippet handling in IPython magic commands.
- Added model mapping functionality and enhanced IPython magic commands.
- Implemented autosaved conversations and enhanced the OpenAI chat models notebook.
- Added new personas for code architect, code writer, and non-technical documentation specialist, along with example persona and snippet files.
- Created a directory for LLM conversations and added test notebooks, argument definitions, and example snippets.
- Enhanced IPython Magic and File Loader functionality.
- Added new notebook examples demonstrating ambient mode handling and other features.

### Changed
- Refactored code across multiple modules to improve readability, maintainability, and formatting, including adjustments to line breaks and import statements.
- Streamlined TYPE_CHECKING usage for conditional imports of requests and yaml.
- Enhanced token usage tracking and reporting in ChatManager and DirectLLMAdapter.
- Updated test cases in `test_cellmage_core.py` and `verify_cellmage.py` for consistency and clarity.
- Upgraded cache action to version 4 to improve performance and compatibility.
- Commented out type checking and mypy cache steps in the CI workflow.

### Removed
- Removed legacy test files for the cellmage library.
- Deleted the model comparison tutorial notebook.

## [v0.1.0](https://github.com/madpin/cellmage/releases/tag/v0.1.0) - 2025-04-26
### Added
- Added a model comparison tutorial notebook for large language model (LLM) evaluation using CellMage.
- Introduced initial integration files and an ambient mode testing notebook.
- Added role specifications for software personas and documented Thiago's profile.
- Included new tutorial notebooks demonstrating CellMage magic functions.
- Added example scripts and comprehensive tests for the CellMage library.
- Created initial test and snippet files.
- Added the CellMage notebook and updated project dependencies.
- Updated the README.md to introduce CellMage and highlight its core features.

### Changed
- Refactored the Settings class to use Pydantic for improved configuration management and added logging settings.
- Improved logging across the project for better traceability.
- Enhanced the CellMage notebook with improved output messages and additional functionality.
- Updated execution times and system messages in the CellMage notebook.
- Enhanced persona loading and error handling in the FileLoader component.
- Refactored LLM integration by removing the LiteLLMAdapter and replacing it with DirectLLMAdapter throughout the codebase; updated configuration handling and notebook examples accordingly.
- Added compatibility for the save_dir setting in configuration.
- Updated project references from 'my-package' to 'cellmage' in all files, including documentation, workflows, and scripts; adjusted installation instructions and versioning details accordingly.
- Removed an unnecessary personalization script and updated changelog preparation and release scripts to reflect the new package name.

### Removed
- Removed the LiteLLMAdapter in favor of the DirectLLMAdapter implementation.
- Removed an unnecessary personalization script as part of the project rename and cleanup.
