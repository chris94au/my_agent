import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


logger = logging.getLogger(__name__)


AUDIT_DB_PATH = Path(__file__).resolve().parent.parent / "tool_events.db"


@dataclass
class ToolParameter:
    name: str
    type: str
    required: bool = True
    description: str = ""
    default: Any = None


@dataclass
class Tool:
    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    execute_fn: Callable[[Any], Any] | None = None
    permission: str = "safe"
    requires_confirmation: bool = False
    accepts_scalar: bool = False
    auto_register: bool = False


    def describe(self):
        parameters = ", ".join(
            f"{parameter.name}:{parameter.type}"
            for parameter in self.parameters
        ) or "keine"

        return (
            f"Tool:\n{self.name}\n\n"
            f"Beschreibung:\n{self.description}\n\n"
            f"Parameter:\n{parameters}"
        )


    def normalize_input(self, input_data):
        if self.accepts_scalar and not isinstance(input_data, dict):
            if len(self.parameters) == 1:
                return {self.parameters[0].name: input_data}

        return input_data


    def validate_input(self, input_data):
        issues = []
        normalized = self.normalize_input(input_data)

        if self.accepts_scalar and not isinstance(normalized, dict):
            if not self.parameters:
                return normalized, issues
            if len(self.parameters) != 1:
                issues.append("Scalar input not supported for this tool")
                return normalized, issues

        if self.parameters and not isinstance(normalized, dict):
            issues.append("Expected a mapping for tool parameters")
            return normalized, issues

        if not self.parameters:
            return normalized, issues

        for parameter in self.parameters:
            if parameter.required and parameter.name not in normalized:
                issues.append(f"Missing required parameter: {parameter.name}")
                continue

            if parameter.name not in normalized:
                continue

            value = normalized[parameter.name]
            if parameter.type == "string" and not isinstance(value, str):
                issues.append(f"Parameter {parameter.name} must be a string")
            elif parameter.type == "integer" and not isinstance(value, int):
                issues.append(f"Parameter {parameter.name} must be an integer")
            elif parameter.type == "number" and not isinstance(value, (int, float)):
                issues.append(f"Parameter {parameter.name} must be a number")
            elif parameter.type == "boolean" and not isinstance(value, bool):
                issues.append(f"Parameter {parameter.name} must be a boolean")
            elif parameter.type == "object" and not isinstance(value, dict):
                issues.append(f"Parameter {parameter.name} must be an object")
            elif parameter.type == "array" and not isinstance(value, list):
                issues.append(f"Parameter {parameter.name} must be an array")

        return normalized, issues


    def execute(self, input_data):
        if self.execute_fn is None:
            raise RuntimeError(f"Tool {self.name} has no execute function")
        return self.execute_fn(input_data)


class ToolRegistry:

    def __init__(self, audit_db_path=AUDIT_DB_PATH):
        self.tools: dict[str, Tool] = {}
        self.audit_db_path = audit_db_path
        self.granted_permissions = {"safe", "math", "time", "filesystem:read", "filesystem:write", "network"}
        self._ensure_audit_table()


    def _ensure_audit_table(self):
        connection = sqlite3.connect(str(self.audit_db_path))
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                agent TEXT,
                tool TEXT,
                input TEXT,
                result TEXT,
                status TEXT,
                runtime_ms REAL,
                error TEXT
            )
            """
        )
        cursor.execute("PRAGMA table_info(tool_events)")
        existing = {row[1] for row in cursor.fetchall()}
        if "runtime_ms" not in existing:
            cursor.execute("ALTER TABLE tool_events ADD COLUMN runtime_ms REAL")
        connection.commit()
        connection.close()


    def register(self, tool: Tool):
        self.tools[tool.name] = tool
        return tool


    def register_many(self, tools):
        for tool in tools:
            self.register(tool)
        return self


    def get(self, name):
        return self.tools.get(name)


    def list_tools(self):
        return list(self.tools.values())


    def get_descriptions(self):
        return "\n".join(
            tool.describe()
            for tool in self.tools.values()
        )


    def set_permissions(self, permissions):
        self.granted_permissions = set(permissions)


    def validate_call(self, tool_name, input_data, confirmed=False):
        tool = self.get(tool_name)
        if tool is None:
            return False, None, [f"Unknown tool: {tool_name}"]

        if tool.permission not in self.granted_permissions and "all" not in self.granted_permissions:
            return False, None, [f"Permission denied for tool: {tool_name}"]

        if tool.requires_confirmation and not confirmed:
            return False, None, [f"Tool requires confirmation: {tool_name}"]

        normalized_input, issues = tool.validate_input(input_data)
        if issues:
            return False, normalized_input, issues

        return True, normalized_input, []


    def _log_event(self, agent, tool, input_data, result, status, runtime_ms=None, error=None):
        connection = sqlite3.connect(str(self.audit_db_path))
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO tool_events (timestamp, agent, tool, input, result, status, runtime_ms, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                agent,
                tool,
                json.dumps(input_data, ensure_ascii=False, default=str),
                json.dumps(result, ensure_ascii=False, default=str),
                status,
                runtime_ms,
                error,
            )
        )
        connection.commit()
        connection.close()


    def execute(self, tool_name, input_data, *, agent="agent", confirmed=False):
        valid, normalized_input, issues = self.validate_call(
            tool_name,
            input_data,
            confirmed=confirmed
        )

        if not valid:
            error = "; ".join(issues) if issues else "Tool validation failed"
            logger.warning("Tool call rejected: %s", error)
            self._log_event(
                agent,
                tool_name,
                input_data,
                {"error": error},
                status="error",
                error=error
            )
            return False, error

        tool = self.get(tool_name)
        start = datetime.now(timezone.utc)
        try:
            result = tool.execute(normalized_input)
            runtime_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000.0
            self._log_event(
                agent,
                tool_name,
                normalized_input,
                result,
                status="ok",
                runtime_ms=runtime_ms,
            )
            return True, result
        except Exception as exc:
            logger.exception("Tool execution failed: %s", tool_name)
            error = f"Fehler beim Ausführen: {exc}"
            runtime_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000.0
            self._log_event(
                agent,
                tool_name,
                normalized_input,
                {"error": error},
                status="error",
                runtime_ms=runtime_ms,
                error=str(exc)
            )
            return False, error


# Backwards compatibility
ToolManager = ToolRegistry

tool_registry = ToolRegistry()
tool_manager = tool_registry
