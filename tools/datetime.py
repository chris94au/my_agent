from datetime import datetime

from .registry import Tool, ToolParameter



def current_time(_):
    return datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )


current_time_tool = Tool(
    name="current_time",
    description="Gibt Datum und Uhrzeit zurück.",
    parameters=[],
    execute_fn=current_time,
    permission="time",
    requires_confirmation=False,
    accepts_scalar=True,
)


tool = current_time_tool
