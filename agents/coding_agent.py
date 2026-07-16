from __future__ import annotations

from typing import Any

import ollama

from .base_agent import BaseAgent
from .contracts import AgentTask


class CodingAgent(BaseAgent):
    def __init__(
        self,
        *,
        name: str = "coding_agent",
        role: str = "coding",
        description: str = "Erzeugt, analysiert und verbessert Code sowie Tests und Dokumentation.",
        system_prompt: str = "",
        capabilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        version: str = "1.0",
        priority: int = 75,
        model: str = "qwen2.5:7b",
    ):
        super().__init__(
            name=name,
            role=role,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities or ["code generation", "analysis", "refactoring", "tests", "documentation"],
            allowed_tools=allowed_tools or ["filesystem:read", "filesystem:write"],
            denied_tools=["web_search", "scheduler", "memory:delete"],
            version=version,
            priority=priority,
        )
        self.model = model


    def _task_text(self, task: Any | None, context_bus, kwargs):
        if isinstance(task, AgentTask):
            return task.input_text or task.goal
        if isinstance(task, dict):
            for key in ("prompt", "goal", "input_text", "input", "text", "message"):
                value = task.get(key)
                if value:
                    return str(value)
        if task is not None:
            return str(task)
        for key in ("prompt", "goal", "task", "user_input"):
            value = kwargs.get(key)
            if value:
                return str(value)
        if context_bus is not None:
            shared = context_bus.get("user_input") if hasattr(context_bus, "get") else None
            if shared:
                return str(shared)
        return ""


    def execute(self, context_bus, task: Any | None = None, **kwargs):
        prompt = self._task_text(task, context_bus, kwargs)
        memory_context = kwargs.get("memory_context")
        if memory_context is None and context_bus is not None:
            memory_context = context_bus.compose_context()
        llm_prompt = f"""
Du bist ein Coding Agent für einen lokalen KI-Agenten.

Aufgabe:
{prompt}

Erlaubte Werkzeuge:
{", ".join(self.allowed_tools) or "keine"}

Kontext:
{memory_context or ""}

Antworte mit einer kompakten technischen Analyse, einem Vorschlag und optional Code oder Testideen.
"""
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": llm_prompt}],
        )
        output = response["message"]["content"]
        result = {
            "prompt": prompt,
            "analysis": output,
            "suggested_changes": [],
            "tests": [],
        }
        if context_bus is not None:
            context_bus.set("coding", result)
            context_bus.publish("coding", result, source=self.name)
            context_bus.add_agent_report(self.name, result)
        return result
