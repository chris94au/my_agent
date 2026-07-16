import logging

from tools import tool_manager


logger = logging.getLogger(__name__)


class ToolExecutor:

    def __init__(self, registry=None):
        self.registry = registry or tool_manager


    def execute(self, tool_name, tool_input, *, agent="agent", confirmed=False):
        success, result = self.registry.execute(
            tool_name,
            tool_input,
            agent=agent,
            confirmed=confirmed,
        )
        if success:
            logger.info(
                "Tool executed successfully: %s",
                tool_name
            )
        else:
            logger.warning(
                "Tool execution failed: %s",
                result
            )
        return success, result
