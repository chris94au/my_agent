from .calculator import calculator, tool as calculator_tool
from .datetime import current_time, tool as current_time_tool
from .filesystem import (
    read_file,
    read_file_tool,
    tool_read_file,
    tool_write_file,
    write_file,
    write_file_tool,
)
from .registry import Tool, ToolManager, ToolParameter, tool_manager, tool_registry
from .web import read_url, read_url_tool, tool, web_search, web_search_tool



tool_manager.register_many(
    [
        calculator_tool,
        current_time_tool,
        read_file_tool,
        write_file_tool,
        web_search_tool,
        read_url_tool,
    ]
)


# Compatibility aliases expected by existing code.
registry = tool_registry
