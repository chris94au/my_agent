from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable


@dataclass(slots=True)
class ContextEvent:
    source: str
    kind: str
    payload: Any
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ContextBus:
    def __init__(self):
        self._lock = RLock()
        self._shared: dict[str, Any] = {}
        self._agent_reports: dict[str, list[Any]] = defaultdict(list)
        self._tool_results: list[dict[str, Any]] = []
        self._sources: list[dict[str, Any]] = []
        self._memory_context: dict[str, Any] = {}
        self._events: list[ContextEvent] = []
        self._subscribers: dict[str, list[Callable[[ContextEvent], None]]] = defaultdict(list)


    def set(self, key: str, value: Any):
        with self._lock:
            self._shared[key] = value
            return value


    def get(self, key: str, default: Any = None):
        with self._lock:
            return self._shared.get(key, default)


    def update(self, values: dict[str, Any]):
        with self._lock:
            self._shared.update(values)
            return dict(self._shared)


    def add_agent_report(self, agent_name: str, report: Any):
        with self._lock:
            self._agent_reports[agent_name].append(report)
            return report


    def get_agent_reports(self, agent_name: str | None = None):
        with self._lock:
            if agent_name is None:
                return {name: list(reports) for name, reports in self._agent_reports.items()}
            return list(self._agent_reports.get(agent_name, []))


    def add_tool_result(self, tool_name: str, result: Any, *, agent_name: str | None = None):
        record = {
            "tool": tool_name,
            "agent": agent_name,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._tool_results.append(record)
            return record


    def add_source(self, source: dict[str, Any] | Any):
        if not isinstance(source, dict):
            source = {"value": source}
        with self._lock:
            self._sources.append(dict(source))
            return source


    def set_memory_context(self, context: dict[str, Any] | str):
        with self._lock:
            self._memory_context = {"value": context} if isinstance(context, str) else dict(context)
            return dict(self._memory_context)


    def get_memory_context(self):
        with self._lock:
            return dict(self._memory_context)


    def publish(self, kind: str, payload: Any, *, source: str = "context_bus"):
        event = ContextEvent(source=source, kind=kind, payload=payload)
        with self._lock:
            self._events.append(event)
            callbacks = list(self._subscribers.get(kind, [])) + list(self._subscribers.get("*", []))
        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                continue
        return event


    def subscribe(self, kind: str, callback: Callable[[ContextEvent], None]):
        with self._lock:
            self._subscribers[kind].append(callback)
            return callback


    def events(self):
        with self._lock:
            return [asdict(event) for event in self._events]


    def clear(self, *, preserve_subscribers: bool = True):
        with self._lock:
            self._shared.clear()
            self._agent_reports.clear()
            self._tool_results.clear()
            self._sources.clear()
            self._memory_context = {}
            self._events.clear()
            if not preserve_subscribers:
                self._subscribers.clear()


    def reset(self):
        self.clear(preserve_subscribers=True)


    def snapshot(self):
        with self._lock:
            return {
                "shared": dict(self._shared),
                "agent_reports": {name: list(reports) for name, reports in self._agent_reports.items()},
                "tool_results": list(self._tool_results),
                "sources": list(self._sources),
                "memory_context": dict(self._memory_context),
                "events": [asdict(event) for event in self._events],
            }


    def compose_context(self):
        snapshot = self.snapshot()
        sections: list[str] = []
        memory_context = snapshot.get("memory_context") or {}
        if memory_context:
            sections.append("Memory Context:")
            if isinstance(memory_context, dict) and "value" in memory_context:
                sections.append(str(memory_context["value"]))
            else:
                sections.append(str(memory_context))
            sections.append("")

        shared = snapshot.get("shared") or {}
        if shared:
            sections.append("Shared Context:")
            for key, value in shared.items():
                sections.append(f"- {key}: {value}")
            sections.append("")

        agent_reports = snapshot.get("agent_reports") or {}
        if agent_reports:
            sections.append("Agent Reports:")
            for agent_name, reports in agent_reports.items():
                sections.append(f"- {agent_name}:")
                for report in reports:
                    sections.append(f"  * {report}")
            sections.append("")

        tool_results = snapshot.get("tool_results") or []
        if tool_results:
            sections.append("Tool Results:")
            for item in tool_results:
                sections.append(f"- {item.get('tool')}: {item.get('result')}")
            sections.append("")

        sources = snapshot.get("sources") or []
        if sources:
            sections.append("Sources:")
            for source in sources:
                sections.append(f"- {source}")
            sections.append("")

        return "\n".join(sections).strip()
