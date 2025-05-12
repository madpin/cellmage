"""
Test script to verify that the _add_to_history method of GitLab and Jira magic works correctly.
"""


# Create a dummy shell for both magic instances
class DummyShell:
    pass


print("Testing GitLab magic _add_to_history method...")
try:
    from cellmage.magic_commands.tools.gitlab_magic import GitLabMagics

    # Create an instance with a dummy shell
    gitlab_magic = GitLabMagics(shell=DummyShell())

    # Try to call _add_to_history method (it will likely return False because we don't have a chat manager,
    # but it shouldn't raise an import error)
    result = gitlab_magic._add_to_history(
        content="Test content", source_type="test", source_id="123", as_system_msg=False
    )
    print(f"✅ GitLabMagics._add_to_history called successfully (returned {result})")

except Exception as e:
    print(f"❌ Error with GitLabMagics: {e}")
    import traceback

    traceback.print_exc()

print("\nTesting Jira magic _add_to_history method...")
try:
    from cellmage.magic_commands.tools.jira_magic import JiraMagics

    # Create an instance with a dummy shell
    jira_magic = JiraMagics(shell=DummyShell())

    # Try to call _add_to_history method (it will likely return False because we don't have a chat manager,
    # but it shouldn't raise an import error)
    result = jira_magic._add_to_history(
        content="Test content", source_type="test", source_id="JIRA-123", as_system_msg=False
    )
    print(f"✅ JiraMagics._add_to_history called successfully (returned {result})")

except Exception as e:
    print(f"❌ Error with JiraMagics: {e}")
    import traceback

    traceback.print_exc()
