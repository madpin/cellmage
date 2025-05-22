from IPython.core.magic import Magics, magics_class, line_magic, cell_magic
from .base_tool_magic import BaseMagics

@magics_class
class DummyToolMagic(BaseMagics):

    @line_magic
    def dummytool(self, line):
        """A dummy line magic that adds its input to history."""
        content = f"DummyTool Line Magic Output: {line}"
        # Use the _add_to_history method from BaseMagics
        # The source_type, source_id, source_name, and id_key can be generic for this dummy tool
        self._add_to_history(
            content=content,
            source_type="dummy_tool_line",
            source_id=line, # Use line content as a simple ID
            source_name="dummytool",
            id_key="dummy_tool_id",
            as_system_msg=False # Or True, depending on how you want to test
        )
        print(content) # Also print to notebook for immediate feedback

    @cell_magic
    def dummymagiccell(self, line, cell):
        """A dummy cell magic that adds its input to history."""
        content = f"DummyTool Cell Magic Output: {line}\n{cell}"
        # Use the _add_to_history method from BaseMagics
        self._add_to_history(
            content=content,
            source_type="dummy_tool_cell",
            source_id=line, # Use line content as a simple ID
            source_name="dummytoolcell",
            id_key="dummy_tool_cell_id",
            as_system_msg=False # Or True
        )
        print(content) # Also print to notebook

def load_ipython_extension(ipython):
    ipython.register_magics(DummyToolMagic)
