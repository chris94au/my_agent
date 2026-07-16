from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from .contracts import AgentTask


class TaskAgent(BaseAgent):
    def __init__(
        self,
        *,
        name: str = "task_agent",
        role: str = "task",
        description: str = "Verwaltet Long-Term Tasks, Status, Resume und Prioritäten.",
        system_prompt: str = "",
        capabilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        version: str = "1.0",
        priority: int = 55,
    ):
        super().__init__(
            name=name,
            role=role,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities or ["long-term tasks", "scheduler", "status", "resume", "priorities"],
            allowed_tools=allowed_tools or [],
            denied_tools=["filesystem:write", "sensitive_actions"],
            version=version,
            priority=priority,
        )
        self._tasks: list[dict[str, Any]] = []
        self._next_id = 1


    def _task_text(self, task: Any | None, context_bus, kwargs):
        if isinstance(task, AgentTask):
            return task.input_text or task.goal
        if isinstance(task, dict):
            return str(task.get("title") or task.get("goal") or task.get("text") or task.get("input") or "")
        if task is not None:
            return str(task)
        for key in ("title", "goal", "task", "text"):
            value = kwargs.get(key)
            if value:
                return str(value)
        if context_bus is not None:
            shared = context_bus.get("task") if hasattr(context_bus, "get") else None
            if shared:
                return str(shared)
        return ""


    def create_task(self, title: str, **kwargs):
        record = {
            "id": self._next_id,
            "title": title,
            "status": kwargs.get("status", "active"),
            "progress": float(kwargs.get("progress", 0.0)),
            "priority": int(kwargs.get("priority", 3)),
            "next_step": kwargs.get("next_step", ""),
            "scheduled_for": kwargs.get("scheduled_for"),
        }
        self._next_id += 1
        self._tasks.append(record)
        return record


    def list_tasks(self):
        return sorted(self._tasks, key=lambda item: (-item.get("priority", 0), item.get("id", 0)))


    def update_task(self, task_id: int, **changes):
        for task in self._tasks:
            if int(task.get("id", 0)) == int(task_id):
                task.update(changes)
                return task
        return None


    def execute(self, context_bus, task: Any | None = None, **kwargs):
        title = self._task_text(task, context_bus, kwargs)
        operation = kwargs.get("operation")
        if isinstance(task, dict):
            operation = task.get("operation", operation)
        operation = str(operation or "create").casefold()

        if operation in {"pause", "resume", "cancel", "prioritize", "update"}:
            task_id = kwargs.get("task_id") or (task.get("task_id") if isinstance(task, dict) else None)
            if operation == "pause":
                result = self.update_task(task_id, status="paused") if task_id is not None else None
            elif operation == "resume":
                result = self.update_task(task_id, status="active") if task_id is not None else None
            elif operation == "cancel":
                result = self.update_task(task_id, status="canceled") if task_id is not None else None
            elif operation == "prioritize":
                priority = kwargs.get("priority", task.get("priority") if isinstance(task, dict) else 3)
                result = self.update_task(task_id, priority=priority) if task_id is not None else None
            else:
                result = self.update_task(task_id, **kwargs)
        else:
            result = self.create_task(title, **kwargs)

        snapshot = self.list_tasks()
        if context_bus is not None:
            context_bus.set("tasks", snapshot)
            context_bus.publish("tasks", snapshot, source=self.name)
            context_bus.add_agent_report(self.name, result or snapshot)
        return result or snapshot
