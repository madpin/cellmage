# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [v0.5.13](https://github.com/madpin/cellmage/releases/tag/v0.5.13) - 2025-05-07

### Added
- Implemented LLM-powered changelog generation supporting multiple models and updated related documentation.
- Added configuration handlers for the `%llm_config` magic command to enhance user configurability.
- Introduced GitHub, Confluence, Jira, and GitLab integrations with corresponding magic commands and utility functions for streamlined workflows.
- Implemented SQLite-based storage for conversation history, including advanced features such as tagging, statistics, and raw API response storage, along with updated documentation and example usage.
- Added support for custom headers in LLM requests and updated configuration settings accordingly.
- Added pre-commit configuration and updated dependencies to enforce code quality checks.
- Added build configuration for Ubuntu 22.04 and Python 3.9 in Read the Docs YAML.
- Added documentation dependencies for Sphinx and related tools to improve documentation build processes.
- Introduced model mapping functionality and enhanced IPython magic commands for better interaction.
- Added autosaved conversations feature and improved OpenAI chat models notebook.
- Added new personas for code architect, code writer, non-technical documentation specialist, and example personas along with corresponding snippets and example files.
- Added initial integration files and ambient mode testing notebook to facilitate development and testing.
- Added CellMage notebook, example script, and comprehensive tests for the cellmage library.
- Added role specifications for software personas and documented Thiago's profile.
- Added new tutorial notebooks for CellMage magic functions and enhanced notebook examples.
- Added support for LaTeX emoji in Read the Docs configuration, re-enabling PDF and EPUB formats.
- Added a new Makefile target and enhanced release scripts to support minor and major version increments and automatic version updates if tags exist.

### Changed
- Refactored release scripts and Makefile to improve version handling, including automatic version updates and support for minor and major version bumps.
- Updated default LLM model references to `gpt-4.1-nano` and later to `gpt-4.1-mini` for improved performance.
- Refactored logging across multiple modules including ChatManager, HistoryManager, and various magic commands to use `logger.debug` for better traceability and improved debug information.
- Refactored IPython magic commands to use a base class for shared functionality, improving maintainability.
- Refactored message deduplication logic in ChatManager to keep the last occurrence of duplicates and preserve system messages from different sources.
- Enhanced persona handling in ChatManager and IPython magic commands with detailed logging for persona requests and system message management.
- Refactored token counting and tracking in ChatManager, HistoryManager, and Jira magic commands to improve accuracy and reporting.
- Refactored header preparation in LLM adapters and updated configuration handling to support new features.
- Refactored code for improved readability and maintainability, including simplifying multi-line statements, adjusting line breaks, and enhancing logging messages.
- Refactored import statements to streamline conditional imports using `TYPE_CHECKING`.
- Refactored snippet directory handling to exclusively use `llm_snippets` and improved test readability in magic command tests.
- Updated README.md to introduce CellMage, clarify features, installation instructions, and author information.
- Updated project references from "my-package" to "cellmage" across all files, including documentation, workflows, and scripts.
- Enhanced virtual environment setup with optional dependencies and caching improvements.
- Enhanced session management with improved session listing output, error handling, and metadata consistency.
- Enhanced IPython context provider with UUID support and enriched response content handling for status information.
- Enhanced ambient mode handling and added new notebook examples.
- Updated linting and formatting configurations to improve code quality.
- Upgraded cache action to v4 for better performance and compatibility.
- Cleaned up whitespace, formatting inconsistencies, and fixed pip install command syntax for consistency.

### Fixed
- Fixed build failures for PDF and EPUB formats in Read the Docs by temporarily commenting out the formats section and later re-enabling it with LaTeX emoji support.
- Corrected installation commands and updated requirements to ensure all optional dependencies are included.
- Fixed token display direction in IPythonContextProvider to correctly indicate input and output tokens.
- Fixed formatting issues in log messages and print statements across multiple files.
- Fixed version update logic in the release script by using separate `sed` commands for clarity.
- Removed unused imports and legacy test files to clean up the codebase.
- Fixed code block syntax in documentation for better clarity and consistency.
- Fixed error handling and improved output formatting in various modules and magic commands.

### Removed
- Deleted obsolete persona and documentation files related to code writer, coder, non-technical documentation specialist, and example personas.
- Removed unused snippets related to EVO, example snippets, and personal details of Thiago.
- Cleared out empty Jupyter notebooks for markdown and model mappings demos.
- Removed version variable and simplified error messages in the `get_default_manager` function.
- Removed legacy test files for the cellmage library.
-


## [v0.5.12](https://github.com/madpin/cellmage/releases/tag/v0.5.12) - 2025-05-07

## [v0.5.11](https://github.com/madpin/cellmage/releases/tag/v0.5.11) - 2025-05-07

## [v0.5.10](https://github.com/madpin/cellmage/releases/tag/v0.5.10) - 2025-05-07

## [v0.5.9](https://github.com/madpin/cellmage/releases/tag/v0.5.9) - 2025-05-07

## [v0.5.8](https://github.com/madpin/cellmage/releases/tag/v0.5.8) - 2025-05-07

## [v0.5.7](https://github.com/madpin/cellmage/releases/tag/v0.5.7) - 2025-05-07

## [v0.5.6](https://github.com/madpin/cellmage/releases/tag/v0.5.6) - 2025-05-07

## [v0.5.5](https://github.com/madpin/cellmage/releases/tag/v0.5.5) - 2025-05-06

## [v0.5.4](https://github.com/madpin/cellmage/releases/tag/v0.5.4) - 2025-05-04

## [v0.5.3](https://github.com/madpin/cellmage/releases/tag/v0.5.3) - 2025-05-04

## [v0.5.2](https://github.com/madpin/cellmage/releases/tag/v0.5.2) - 2025-05-04

## [v0.5.1](https://github.com/madpin/cellmage/releases/tag/v0.5.1) - 2025-05-03

## [v0.5.0](https://github.com/madpin/cellmage/releases/tag/v0.5.0) - 2025-05-03

## [v0.4.7](https://github.com/madpin/cellmage/releases/tag/v0.4.7) - 2025-05-01

## [v0.4.6](https://github.com/madpin/cellmage/releases/tag/v0.4.6) - 2025-05-01

## [v0.4.5](https://github.com/madpin/cellmage/releases/tag/v0.4.5) - 2025-05-01

## [v0.4.4](https://github.com/madpin/cellmage/releases/tag/v0.4.4) - 2025-05-01

## [v0.4.3](https://github.com/madpin/cellmage/releases/tag/v0.4.3) - 2025-05-01

## [v0.4.2](https://github.com/madpin/cellmage/releases/tag/v0.4.2) - 2025-04-29


## [v0.4.1](https://github.com/madpin/cellmage/releases/tag/v0.4.1) - 2025-04-29

## [v0.4.0](https://github.com/madpin/cellmage/releases/tag/v0.4.0) - 2025-04-29

## [v0.3.1](https://github.com/madpin/cellmage/releases/tag/v0.3.1) - 2025-04-29

## [v0.3.0](https://github.com/madpin/cellmage/releases/tag/v0.3.0) - 2025-04-29

## [v0.2.5](https://github.com/madpin/cellmage/releases/tag/v0.2.5) - 2025-04-29

## [v0.2.4](https://github.com/madpin/cellmage/releases/tag/v0.2.4) - 2025-04-29

## [v0.2.3](https://github.com/madpin/cellmage/releases/tag/v0.2.3) - 2025-04-29

## [v0.2.2](https://github.com/madpin/cellmage/releases/tag/v0.2.2) - 2025-04-29

## [v0.2.1](https://github.com/madpin/cellmage/releases/tag/v0.2.1) - 2025-04-28

## [v0.2.0](https://github.com/madpin/cellmage/releases/tag/v0.2.0) - 2025-04-28

## [v0.1.3](https://github.com/madpin/cellmage/releases/tag/v0.1.3) - 2025-04-28

## [v0.1.2](https://github.com/madpin/cellmage/releases/tag/v0.1.2) - 2025-04-28

## [v0.1.1](https://github.com/madpin/cellmage/releases/tag/v0.1.1) - 2025-04-28

## [v0.1.0](https://github.com/madpin/cellmage/releases/tag/v0.1.0) - 2025-04-26
