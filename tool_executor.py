import logging

from tools import tool_manager


logger = logging.getLogger(__name__)


class ToolExecutor:

    def __init__(self, registry=None):
        self.registry = registry or tool_manager


    def execute(self, tool_name, tool_input, *, agent="agent", confirmed=False):
        valid, normalized_input, issues = self.registry.validate_call(
            tool_name,
            tool_input,
            confirmed=confirmed
        )

        if not valid:
            error = "; ".join(issues) if issues else f"Unbekanntes Werkzeug: {tool_name}"
            logger.warning(
                "Tool validation failed for %s: %s",
                tool_name,
                error
            )
            return False, error

        tool = self.registry.get(tool_name)
        if tool is None:
            return False, f"Unbekanntes Werkzeug: {tool_name}"

        try:
            result = tool.execute(normalized_input)
            logger.info(
                "Tool executed successfully: %s",
                tool_name
            )
            return True, result
        except Exception as e:
            logger.exception(
                "Tool execution failed: %s",
                tool_name
            )
            return False, f"Fehler beim Ausführen: {e}"
