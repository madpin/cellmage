"""
Test direct import of the problematic modules to verify our fix.
"""

print("Attempting direct import of modules...")

try:

    print("✅ All magic modules imported successfully")

except Exception as e:
    print(f"❌ Error importing modules: {e}")
    import traceback

    traceback.print_exc()

print("\nVerifying models import in base_tools_magic...")
try:
    # This is the import that was failing

    print("✅ Successfully imported Message from cellmage.magic_commands.models")

except Exception as e:
    print(f"❌ Error importing Message: {e}")
    import traceback

    traceback.print_exc()
