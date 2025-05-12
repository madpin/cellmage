#!/usr/bin/env python
"""
CellMage Extension Diagnostic Tool

This script checks the status of the CellMage extension and its components.
It's intended to be run directly from the command line to diagnose extension issues.

Usage:
    python diagnostics.py

"""

import importlib
import pkgutil


def check_import(module_name):
    """Try to import a module and return True if successful."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError as e:
        print(f"❌ Error importing {module_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing {module_name}: {e}")
        return False


def main():
    print("===== CellMage Extension Diagnostics =====")

    # Check base packages
    print("\nChecking core packages:")
    core_packages = [
        "cellmage",
        "cellmage.magic_commands",
        "cellmage.magic_commands.ipython",
        "cellmage.magic_commands.tools",
        "cellmage.integrations",
    ]

    for package in core_packages:
        if check_import(package):
            print(f"✅ {package} - Successfully imported")

    # Check the load_ipython_extension function in tools/__init__.py
    print("\nChecking tool loading function:")
    try:
        import cellmage.magic_commands.tools

        loader = getattr(cellmage.magic_commands.tools, "load_ipython_extension", None)
        if callable(loader):
            print("✅ cellmage.magic_commands.tools.load_ipython_extension - Function exists")
            # Check return type annotation
            import inspect

            sig = inspect.signature(loader)
            ret_annotation = sig.return_annotation
            if ret_annotation == list[str] or ret_annotation == "List[str]":
                print(f"✅ Return type annotation is correct: {ret_annotation}")
            else:
                print(f"⚠️ Return type annotation might need fixing: {ret_annotation}")
        else:
            print("❌ load_ipython_extension function not found in tools module")
    except Exception as e:
        print(f"❌ Error checking tools loader function: {e}")

    # List available magic tools
    print("\nChecking magic tool modules:")
    try:
        import cellmage.magic_commands.tools as tools_pkg

        for finder, mod_name, _ in pkgutil.iter_modules(tools_pkg.__path__):
            if mod_name == "__pycache__":
                continue

            full_name = f"{tools_pkg.__name__}.{mod_name}"
            try:
                module = importlib.import_module(full_name)
                has_load_ext = hasattr(module, "load_ipython_extension")
                status = "✅" if has_load_ext else "⚠️"
                ext_info = (
                    "has load_ipython_extension" if has_load_ext else "no load_ipython_extension"
                )
                print(f"{status} {full_name} - {ext_info}")
            except ImportError as e:
                print(f"❌ {full_name} - Import error: {e}")
            except Exception as e:
                print(f"❌ {full_name} - Error: {e}")
    except Exception as e:
        print(f"❌ Error checking magic tools: {e}")

    # List available integrations
    print("\nChecking integration modules:")
    try:
        import cellmage.integrations as integrations_pkg

        for finder, mod_name, _ in pkgutil.iter_modules(integrations_pkg.__path__):
            if mod_name == "__pycache__":
                continue

            full_name = f"{integrations_pkg.__name__}.{mod_name}"
            try:
                module = importlib.import_module(full_name)
                print(f"✅ {full_name} - Successfully imported")
            except ImportError as e:
                print(f"❌ {full_name} - Import error: {e}")
            except Exception as e:
                print(f"❌ {full_name} - Error: {e}")
    except Exception as e:
        print(f"❌ Error checking integration modules: {e}")

    print("\n===== Diagnostics Complete =====")
    print("To test the extension in IPython, run:")
    print("  %run test_extension.py")


if __name__ == "__main__":
    main()
