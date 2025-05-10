# Magic Commands Testing Strategy

This document outlines the comprehensive testing strategy for CellMage's magic commands.

## Overview

CellMage's magic commands are tested using a comprehensive suite of unit tests. These tests verify that each magic command works correctly in isolation and that the various components work together properly. The testing approach includes:

1. **Unit tests** - Testing individual components in isolation
2. **Integration tests** - Testing how components work together
3. **Mock testing** - Using mocks to simulate dependencies
4. **Test fixtures** - Reusable test environments and utilities

## Test Structure

The test suite is organized as follows:

```
tests/
├── unit/
│   ├── magic_commands/                # Base test classes and utilities
│   │   ├── test_base.py               # Base test class with common fixtures
│   │   ├── config_handler_test_utils.py # Utilities for testing handlers
│   │   └── ...
│   ├── test_config_handlers.py        # Tests for config handlers
│   ├── test_integration_magics.py     # Tests for integration magics
│   ├── test_ambient_mode.py           # Tests for ambient mode
│   ├── test_common_magic.py           # Tests for common magic functionality
│   └── ...
└── run_magic_tests.py                 # Script to run all magic tests
```

## Base Test Class

All magic command tests inherit from `MagicCommandsTestBase`, which provides:

- Common fixtures for IPython, shell, and other dependencies
- Utility methods for testing magic commands
- Decorators for skipping tests when IPython is not available

Example:

```python
from tests.unit.magic_commands.test_base import MagicCommandsTestBase, ipython_required

class TestYourMagic(MagicCommandsTestBase):
    def setUp(self):
        super().setUp()
        # Your setup code

    @ipython_required
    def test_your_feature(self):
        # Test code
```

## Test Categories

### 1. Core Magic Tests

Tests for the core magic command functionality:
- Configuration magic (`%llm_config`)
- LLM interaction magic (`%llm`, `%%llm`)
- Ambient mode management

### 2. Handler Tests

Tests for the individual handler classes used by the configuration magic:
- PersonaConfigHandler
- OverrideConfigHandler
- HistoryDisplayHandler
- etc.

### 3. Integration Tests

Tests for the integration magic commands:
- GitHub integration
- Confluence integration
- Jira integration
- Google Docs integration
- etc.

### 4. Ambient Mode Tests

Tests for the ambient mode functionality:
- Activation/deactivation
- Event handling
- Code generation

## Running the Tests

To run all the magic command tests:

```bash
# Run tests with pytest (default)
python tests/run_magic_tests.py

# Run tests with unittest
python tests/run_magic_tests.py --unittest
```

To run specific test modules:

```bash
python -m pytest tests/unit/test_llm_magic.py
```

## Creating New Tests

Use the `create_magic_test.py` script to generate test files for new magic commands:

```bash
python tests/create_magic_test.py
```

This script will guide you through creating a new test file with:
- Appropriate imports and base class
- Test methods for the functionality you need to test
- Standard test structure

## Best Practices

### 1. Mock External Dependencies

Use `unittest.mock` to isolate the code under test from external dependencies:

```python
with patch("cellmage.some_module.some_function") as mock_function:
    # Set up return value or side effect
    mock_function.return_value = "test value"

    # Run the code that uses the dependency
    result = self.magic_instance.some_method()

    # Verify the mock was called correctly
    mock_function.assert_called_once_with(expected_args)
```

### 2. Test All Code Paths

Ensure you test all meaningful code paths, including:
- Success cases (happy path)
- Error cases (when things go wrong)
- Edge cases (boundary conditions)

### 3. Use Descriptive Test Names

Name tests based on what they're testing, for clarity:

```python
def test_persona_handler_activates_persona_correctly(self):
    # Test code
```

### 4. Keep Tests Independent

Tests should not depend on each other. Each test should:
- Set up its own test environment
- Clean up after itself
- Work regardless of which other tests are run

### 5. Check for IPython

Use the `ipython_required` decorator for tests that need IPython:

```python
@ipython_required
def test_ipython_dependent_feature(self):
    # This test will be skipped if IPython is not available
```

## Common Test Patterns

### Testing Line Magic

```python
@ipython_required
def test_line_magic(self):
    # Create mock args
    args = MagicMock()
    args.some_flag = True

    # Mock any dependencies
    with patch("module.dependency") as mock_dep:
        # Execute the magic
        result = self.magic_instance.some_magic("args")

    # Verify the result
    self.assertEqual(result, expected_value)
    mock_dep.assert_called_once_with(expected_args)
```

### Testing Cell Magic

```python
@ipython_required
def test_cell_magic(self):
    # Create cell content
    cell = "Test cell content"

    # Execute the magic
    with patch("builtins.print") as mock_print:
        result = self.magic_instance.some_cell_magic("args", cell)

    # Verify the magic executed correctly
    mock_print.assert_called_with(expected_output)
```

## Future Improvements

1. Add more test coverage for edge cases
2. Create dedicated test fixtures for specific scenarios
3. Implement property-based testing for complex input scenarios
4. Add integration tests with actual IPython sessions

## Creating New Tests

To create a new test for a magic command:

1. Use the template generator:
   ```bash
   python tests/create_magic_test.py
   ```

2. Follow the prompts to create a new test file.

3. Implement the test methods in the generated file.

4. Add the new test module to `tests/run_magic_tests.py`.

## Test Coverage

The tests aim to cover:

- **Command Registration**: Verifying that magic commands are properly registered with IPython.
- **Argument Parsing**: Testing that command arguments are parsed correctly.
- **Handler Execution**: Ensuring that the appropriate handlers are called for each command.
- **Integration**: Testing that magic commands interact correctly with other components.
- **Edge Cases**: Testing behavior with invalid or edge case inputs.

## Mocking Strategy

The tests use mocks to isolate the magic commands from their dependencies:

- **IPython Environment**: Mock IPython shell and input/output.
- **Chat Manager**: Mock the chat manager and its components.
- **Context Provider**: Mock the context provider for cell information.
- **External Services**: Mock external services like GitHub, Confluence, etc.

## Adding New Magic Commands

When adding a new magic command:

1. Create tests for the new magic command using the template generator.
2. Ensure that the tests cover all functionality of the new command.
3. Add the new tests to the test suite in `run_magic_tests.py`.
4. Verify that all tests pass before submitting a pull request.

## Testing Best Practices

- Keep tests focused on a single piece of functionality.
- Use descriptive method names that explain what is being tested.
- Use appropriate assertions to verify the expected behavior.
- Mock external dependencies to isolate the code being tested.
- Test both success and failure cases.
- Test edge cases and invalid inputs.
