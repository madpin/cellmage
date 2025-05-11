#!/usr/bin/env python
"""
Test runner for CellMage magic commands.

This script runs all tests for the magic commands and reports the results.
"""

import importlib
import sys
from pathlib import Path
from unittest import TestLoader, TestSuite, TextTestRunner

import pytest


def discover_magic_test_modules():
    """Automatically discover all magic-related test modules."""
    test_modules = []

    # Get the base directory of the tests
    base_dir = Path(__file__).parent

    # Look for test_*magic*.py files in unit directory
    unit_dir = base_dir / "unit"
    if unit_dir.exists():
        for file_path in unit_dir.glob("test_*magic*.py"):
            module_name = f"tests.unit.{file_path.stem}"
            test_modules.append(module_name)

    # Include the ambient mode tests
    ambient_path = unit_dir / "test_ambient_mode.py"
    if ambient_path.exists():
        test_modules.append("tests.unit.test_ambient_mode")

    # Include the config handlers tests
    config_handlers_path = unit_dir / "test_config_handlers.py"
    if config_handlers_path.exists():
        test_modules.append("tests.unit.test_config_handlers")

    # Include integration magic tests
    integration_magics_path = unit_dir / "test_integration_magics.py"
    if integration_magics_path.exists():
        test_modules.append("tests.unit.test_integration_magics")

    # Include magic commands specific tests
    magic_cmds_dir = unit_dir / "magic_commands"
    if magic_cmds_dir.exists():
        for file_path in magic_cmds_dir.glob("test_*.py"):
            if file_path.name != "__init__.py" and file_path.name != "test_base.py":
                module_name = f"tests.unit.magic_commands.{file_path.stem}"
                test_modules.append(module_name)

    # Include the original magic commands test
    magic_commands_path = unit_dir / "test_magic_commands.py"
    if magic_commands_path.exists():
        test_modules.append("tests.unit.test_magic_commands")

    return test_modules


def run_magic_tests_unittest():
    """Run all magic command tests using unittest."""
    # Add the project root to the path for better imports
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # Create a test loader
    loader = TestLoader()

    # Automatically discover test modules
    test_modules = discover_magic_test_modules()

    if not test_modules:
        print("No magic command test modules found!")
        return False

    print(f"Found {len(test_modules)} test modules:")
    for module in sorted(test_modules):
        print(f"  - {module}")

    # Create a test suite
    suite = TestSuite()

    # Add tests from all modules
    for module_name in sorted(test_modules):
        try:
            # First try to import the module to catch any import errors
            try:
                importlib.import_module(module_name)
                print(f"Successfully imported {module_name}")
            except ImportError as e:
                print(f"Error importing {module_name}: {e}")
                continue

            # Then load tests from the module
            tests = loader.loadTestsFromName(module_name)
            suite.addTests(tests)
            print(f"Added tests from {module_name}")
        except (ImportError, ValueError, AttributeError) as e:
            print(f"Could not load tests from {module_name}: {e}")

    # Run the tests
    runner = TextTestRunner(verbosity=2)
    print("\nRunning magic command tests...\n")
    result = runner.run(suite)

    # Return the success status
    return result.wasSuccessful()


def run_magic_tests_pytest():
    """Run all magic command tests using pytest."""
    # Add the project root to the path for better imports
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    print("\n" + "=" * 80)
    print("Running Magic Command Tests with pytest")
    print("=" * 80 + "\n")

    # Specify test files individually
    test_files = []
    unit_dir = project_root / "tests" / "unit"

    # Add magic test files
    for pattern in [
        "test_*magic*.py",
        "test_config_handlers.py",
        "test_ambient_mode.py",
        "test_integration_magics.py",
    ]:
        matching_files = list(unit_dir.glob(pattern))
        test_files.extend(matching_files)

    # Add magic_commands directory tests
    magic_cmd_dir = unit_dir / "magic_commands"
    if magic_cmd_dir.exists():
        test_files.extend(list(magic_cmd_dir.glob("test_*.py")))

    # Convert paths to strings
    test_file_paths = [str(f) for f in test_files]

    if not test_file_paths:
        print("No test files found!")
        return False

    # Print found test files
    print(f"Found {len(test_file_paths)} test files:")
    for f in sorted(test_file_paths):
        print(f"  {f}")

    # Run the tests with pytest
    return pytest.main(["-v"] + test_file_paths) == 0


def run_magic_tests(use_pytest=True):
    """Run all magic command tests using the specified test runner."""
    if use_pytest:
        return run_magic_tests_pytest()
    else:
        return run_magic_tests_unittest()


if __name__ == "__main__":
    # Default to pytest, but allow falling back to unittest via command line flag
    use_pytest = "--unittest" not in sys.argv
    success = run_magic_tests(use_pytest=use_pytest)
    sys.exit(0 if success else 1)
