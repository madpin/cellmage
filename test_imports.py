#!/usr/bin/env python
"""
Test imports after refactoring.

This script checks various imports in the CellMage package to ensure
they are working correctly after the refactoring.
"""

import importlib
import sys
import traceback


def test_import(module_name, detailed=False):
    """Test importing a specific module."""
    try:
        importlib.import_module(module_name)
        print(f"✅ Successfully imported {module_name}")
        return True
    except ImportError as e:
        print(f"❌ Error importing {module_name}: {e}")
        if detailed:
            print("Detailed traceback:")
            traceback.print_exc(file=sys.stdout)
        return False
    except Exception as e:
        print(f"❗ Unexpected error importing {module_name}: {e}")
        if detailed:
            print("Detailed traceback:")
            traceback.print_exc(file=sys.stdout)
        return False


def main():
    print("🔍 Testing CellMage imports after refactoring\n")

    # Test core imports
    print("Testing core imports:")
    test_import("cellmage")

    # Test magic commands base
    print("\nTesting magic commands base:")
    test_import("cellmage.magic_commands")

    # Test tools package
    print("\nTesting tools package:")
    test_import("cellmage.magic_commands.tools", detailed=True)

    # Test specific tool modules
    print("\nTesting base tools magic:")
    test_import("cellmage.magic_commands.tools.base_tools_magic", detailed=True)

    # Test integration modules
    print("\nTesting integration modules:")
    test_import("cellmage.integrations")
    test_import("cellmage.integrations.github_utils")

    print("\n✅ Import tests completed")


if __name__ == "__main__":
    main()
