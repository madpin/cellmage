# Refactored Magic Commands Architecture

## Overview

The CellMage package has been refactored to improve the organization of its IPython magic commands. The previous monolithic implementation in `ipython_magic.py` has been split into separate, focused modules that follow the single responsibility principle.

This document explains the new architecture and how to extend it.

## Directory Structure

The magic commands are now organized in the following structure:

```
cellmage/magic_commands/
├── __init__.py       # Entry point for loading all magic commands
├── core.py           # Shared utilities for all magic types
├── ipython/
│   ├── __init__.py   # Entry point for IPython-specific magic commands
│   ├── common.py     # Shared utilities for IPython magic commands
│   ├── config_magic.py    # %llm_config implementation
│   ├── llm_magic.py       # %%llm implementation
│   └── ambient_magic.py   # Ambient mode and %%py implementation
```

## Components

### Magic Base Classes

- `IPythonMagicsBase`: Base class for all IPython magic commands, providing common functionality like chat manager access and runtime parameter handling.

### Magic Command Modules

Each module is focused on a specific type of functionality:

1. **llm_magic.py**: Implements the `%%llm` cell magic for sending prompts to LLMs.
2. **config_magic.py**: Implements the `%llm_config` line magic for configuring settings.
3. **ambient_magic.py**: Implements ambient mode-related functionality.

### Loading Mechanism

The magic commands are loaded through a hierarchy of loader functions:

1. `cellmage.load_ipython_extension(ipython)`: Main entry point called by IPython
2. `cellmage.magic_commands.load_ipython_extension(ipython)`: Delegates to specific magic type loaders
3. `cellmage.magic_commands.ipython.load_magics(ipython)`: Loads all IPython-specific magic commands

## Benefits of the New Architecture

1. **Separation of Concerns**: Each magic class has a clear, focused responsibility
2. **Improved Maintainability**: Smaller files are easier to understand and modify
3. **Better Testability**: Components can be tested in isolation
4. **Easier Extension**: New magic commands can be added without modifying existing ones
5. **Cleaner Imports**: Reduced circular dependencies and unnecessary imports

## How to Extend

### Adding a New Magic Command

To add a new magic command:

1. Create a new file in the appropriate directory (e.g., `ipython/new_magic.py`)
2. Implement a class that extends `IPythonMagicsBase`
3. Use the `@magics_class` decorator on your class
4. Add your magic methods with appropriate decorators (`@line_magic`, `@cell_magic`)
5. Register your class in the appropriate `__init__.py` file

Example:

```ipython
# in ipython/new_magic.py
@magics_class
class NewMagics(IPythonMagicsBase):
    @line_magic("my_new_magic")
    def my_new_magic(self, line):
        """Documentation for the magic."""
        # Implementation
        pass

# in ipython/__init__.py
def load_magics(ipython):
    from .new_magic import NewMagics
    ipython.register_magics(NewMagics)
```

### Extending Existing Magic Commands

To extend functionality in an existing magic command:

1. Modify the appropriate file (e.g., `config_magic.py` for `%llm_config`)
2. Add new methods or parameters as needed
3. Update the argument parser if adding new command line options

## Fallback Mechanism

The system includes a fallback mechanism to the legacy monolithic implementation to ensure backward compatibility. If the refactored implementation fails to load, the system will attempt to load the legacy implementation.

## Testing

The refactored architecture includes both unit tests and integration tests:

- Unit tests verify the behavior of individual components
- Integration tests ensure the components work together correctly

Tests can be run with the standard testing framework:

```
pytest tests/unit/test_magic_commands.py
pytest tests/integration/test_refactored_magics.py
```
