#!/usr/bin/env python
"""
Template generator for CellMage magic command tests.

This script creates a new test file for magic commands with the appropriate imports and structure.
"""

import os

TEST_TEMPLATE = '''"""
Tests for {magic_name} functionality.

This module tests the {magic_description}.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from .magic_commands.test_base import MagicCommandsTestBase, ipython_required


class Test{class_name}(MagicCommandsTestBase):
    """Tests for the {magic_name} functionality."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        # Import the module under test
        {import_code}
        self.{instance_name} = {class_name}(self.mock_ipython)

{test_methods}

if __name__ == "__main__":
    pytest.main([__file__])
'''

TEST_METHOD_TEMPLATE = '''    @ipython_required
    def test_{method_name}(self):
        """Test {test_description}."""
        # TODO: Implement test
        pass
'''


def create_new_test(magic_name, magic_description, class_name, module_path, method_names=None):
    """Create a new test file for a magic command."""
    # Generate instance name from class name
    instance_name = class_name[0].lower() + class_name[1:] if class_name else "magic"

    # Generate import code
    import_code = f"from {module_path} import {class_name}"

    # Generate test methods
    test_methods = ""
    if method_names:
        for method_name, description in method_names.items():
            test_methods += TEST_METHOD_TEMPLATE.format(
                method_name=method_name, test_description=description
            )
    else:
        # Add a default test method
        test_methods = TEST_METHOD_TEMPLATE.format(
            method_name="basic_functionality",
            test_description="basic functionality of the magic command",
        )

    # Format the test file content
    test_content = TEST_TEMPLATE.format(
        magic_name=magic_name,
        magic_description=magic_description,
        class_name=class_name,
        import_code=import_code,
        instance_name=instance_name,
        test_methods=test_methods,
    )

    # Create the file path
    file_name = f"test_{magic_name.lower().replace(' ', '_')}.py"
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "unit", file_name)

    # Create the file
    with open(file_path, "w") as f:
        f.write(test_content)

    print(f"Created test file at {file_path}")
    return file_path


def interactive_create():
    """Interactively create a new test file."""
    print("=== CellMage Magic Command Test Generator ===")

    magic_name = input("Enter magic command name (e.g. 'LLM Magic'): ")
    magic_description = input("Enter magic command description: ")
    class_name = input("Enter magic class name (e.g. 'CoreLLMMagics'): ")
    module_path = input(
        "Enter module import path (e.g. 'cellmage.magic_commands.ipython.llm_magic'): "
    )

    method_names = {}
    print("\nEnter test methods (leave blank to finish):")
    while True:
        method_name = input("  Method name (e.g. 'execute_llm_with_persona'): ")
        if not method_name:
            break
        description = input(f"  Description for {method_name}: ")
        method_names[method_name] = description

    file_path = create_new_test(
        magic_name, magic_description, class_name, module_path, method_names
    )
    print(f"\nTest file created at: {file_path}")
    print("Don't forget to add the new test to tests/run_magic_tests.py")


if __name__ == "__main__":
    interactive_create()
