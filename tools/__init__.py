from tool_manager import Tool, ToolManager

from .calculator import calculator
from .datetime_tool import current_time
from .filesystem import read_file, write_file



tool_manager = ToolManager()



tool_manager.register(
    Tool(
        "calculator",
        "Berechnet mathematische Ausdrücke",
        calculator
    )
)



tool_manager.register(
    Tool(
        "current_time",
        "Gibt Datum und Uhrzeit zurück",
        current_time
    )
)



tool_manager.register(
    Tool(
        "read_file",
        "Liest eine Datei aus dem Workspace",
        read_file
    )
)



tool_manager.register(
    Tool(
        "write_file",
        "Schreibt eine Datei in den Workspace",
        write_file
    )
)