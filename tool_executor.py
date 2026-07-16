from tools import tool_manager


class ToolExecutor:

    def execute(self, tool_name, tool_input):

        tool = tool_manager.get(tool_name)

        if tool is None:
            return False, f"Unbekanntes Werkzeug: {tool_name}"

        try:
            result = tool.execute(tool_input)
            return True, result

        except Exception as e:
            return False, f"Fehler beim Ausführen: {e}"