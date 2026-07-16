from pathlib import Path
from datetime import datetime
from tool_manager import Tool, ToolManager

WORKSPACE = Path("./workspace")


def calculator(expression):

    try:
        result = eval(expression)
        return str(result)

    except Exception as e:
        return f"Fehler beim Rechnen: {e}"



def current_time(_):

    return datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )



def read_file(filename):

    try:

        file_path = WORKSPACE / filename

        if not file_path.exists():
            return f"Datei {filename} existiert nicht."

        return file_path.read_text(
            encoding="utf-8"
        )


    except Exception as e:

        return f"Fehler beim Lesen: {e}"



def write_file(data):

    try:

        WORKSPACE.mkdir(
            exist_ok=True
        )


        filename = data["filename"]
        content = data["content"]


        file_path = WORKSPACE / filename


        file_path.write_text(
            content,
            encoding="utf-8"
        )


        return f"Datei {filename} wurde erfolgreich gespeichert."


    except Exception as e:

        return f"Fehler beim Schreiben: {e}"



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