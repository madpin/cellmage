#!/usr/bin/env python
"""
Debug script for tools module imports.
"""

import importlib
import pkgutil
import sys
import traceback

# Add current directory to path
sys.path.insert(0, ".")

# Force output flushing
sys.stdout.reconfigure(line_buffering=True)


def main():
    print("=== CellMage Import Debug ===")
    print(f"Python: {sys.executable}")
    print(f"Path: {sys.path[0]}")
    print()

    try:
        print("Attempting to import cellmage...")
        import cellmage

        print(f"✅ cellmage imported successfully (version: {cellmage.__version__})")

        print("\nAttempting to import magic_commands...")
        import cellmage.magic_commands

        print("✅ magic_commands imported successfully")

        # Try tools module
        print("\nAttempting to import tools module...")
        try:
            import cellmage.magic_commands.tools

            print("✅ tools module imported successfully")

            # List tool modules
            print("\nListing available tool modules:")
            import cellmage.magic_commands.tools as tools_pkg

            for finder, mod_name, ispkg in pkgutil.iter_modules(tools_pkg.__path__):
                if mod_name == "__pycache__":
                    continue

                print(f"  - {mod_name}")

                # Test importing each module
                try:
                    full_name = f"{tools_pkg.__name__}.{mod_name}"
                    importlib.import_module(full_name)
                    print(f"    ✅ {mod_name} imported successfully")
                except Exception as e:
                    print(f"    ❌ Error importing {mod_name}: {e}")

        except ImportError as e:
            print(f"❌ Error importing tools module: {e}")
            traceback.print_exc()

        # Try calling the function
        print("\nTesting tools.load_ipython_extension function...")
        try:
            from cellmage.magic_commands.tools import load_ipython_extension

            print("✅ Function imported successfully")
            print(f"Function signature: {load_ipython_extension.__annotations__}")

            # Try to call it (it will fail without IPython, that's ok)
            try:
                tools = load_ipython_extension(None)
                print(f"Function returned: {tools}")
            except Exception as e:
                print(f"Expected error calling function: {e}")

        except ImportError as e:
            print(f"❌ Error importing load_ipython_extension: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()

    print("\n=== Debug Complete ===")


if __name__ == "__main__":
    main()
