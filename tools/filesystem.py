from pathlib import Path

from .registry import Tool, ToolParameter


WORKSPACE = Path("./workspace").resolve()



def _safe_path(filename):
    target = (WORKSPACE / str(filename)).resolve()
    try:
        target.relative_to(WORKSPACE)
    except ValueError:
        raise ValueError("Ungültiger Dateipfad außerhalb des Workspace")
    return target



def read_file(input_data):
    try:
        filename = input_data.get("filename") if isinstance(input_data, dict) else input_data
        file_path = _safe_path(filename)

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

        file_path = _safe_path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(
            content,
            encoding="utf-8"
        )

        return (
            f"Datei {filename} wurde erfolgreich gespeichert."
        )

    except Exception as e:
        return f"Fehler beim Schreiben: {e}"


read_file_tool = Tool(
    name="read_file",
    description="Liest eine Datei aus dem Workspace.",
    parameters=[
        ToolParameter(
            name="filename",
            type="string",
            required=True,
            description="Pfad relativ zum Workspace"
        )
    ],
    execute_fn=read_file,
    permission="filesystem:read",
    requires_confirmation=False,
    accepts_scalar=True,
)


write_file_tool = Tool(
    name="write_file",
    description="Schreibt eine Datei in den Workspace.",
    parameters=[
        ToolParameter(
            name="filename",
            type="string",
            required=True,
            description="Pfad relativ zum Workspace"
        ),
        ToolParameter(
            name="content",
            type="string",
            required=True,
            description="Dateiinhalt"
        )
    ],
    execute_fn=write_file,
    permission="filesystem:write",
    requires_confirmation=False,
    accepts_scalar=False,
)


tool_read_file = read_file_tool
tool_write_file = write_file_tool
