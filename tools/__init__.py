from tool_manager import Tool, ToolManager

from .calculator import calculator
from .datetime_tool import current_time
from .filesystem import read_file, write_file
from .internet_research import web_search, read_url



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



tool_manager.register(
    Tool(
        "web_search",
        "Durchsucht das Internet frei, priorisiert Ergebnisse mit einem dynamischen Glossar informativer Websites und aktualisiert dieses Glossar beim Lesen von Seiten. Das Glossar ist auf 1000 Seiten begrenzt.",
        web_search
    )
)



tool_manager.register(
    Tool(
        "read_url",
        "Öffnet eine URL und liest Textseiten direkt. Nicht-textuelle Inhalte oder Downloads werden nur nach ausdrücklicher Bestätigung gespeichert und nie automatisch geöffnet.",
        read_url
    )
)
