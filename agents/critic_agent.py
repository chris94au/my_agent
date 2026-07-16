from __future__ import annotations

from typing import Any

from critic import Critic

from .base_agent import BaseAgent
from .contracts import AgentTask


class CriticAgent(BaseAgent):
    def __init__(
        self,
        *,
        name: str = "critic_agent",
        role: str = "critic",
        description: str = "Prüft Fakten, Logik, Vollständigkeit, Tool-Verwendung und Quellen.",
        system_prompt: str = "",
        capabilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        version: str = "1.0",
        priority: int = 90,
        model: str = "qwen2.5:7b",
        critic_cls=Critic,
    ):
        super().__init__(
            name=name,
            role=role,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities or ["fact checking", "logic", "completeness", "tool review", "source review"],
            allowed_tools=allowed_tools or [],
            denied_tools=["filesystem:write", "scheduler"],
            version=version,
            priority=priority,
        )
        self.model = model
        self.critic = critic_cls(model=model)


    def _task_text(self, task: Any | None, context_bus, kwargs):
        if isinstance(task, AgentTask):
            return task.input_text or task.goal
        if isinstance(task, dict):
            for key in ("final_answer", "answer", "text", "goal", "input_text", "input"):
                value = task.get(key)
                if value:
                    return str(value)
        if task is not None:
            return str(task)
        for key in ("final_answer", "answer", "text"):
            value = kwargs.get(key)
            if value:
                return str(value)
        if context_bus is not None:
            shared = context_bus.get("final_answer") if hasattr(context_bus, "get") else None
            if shared:
                return str(shared)
        return ""


    def execute(self, context_bus, task: Any | None = None, **kwargs):
        plan = kwargs.get("plan")
        if plan is None and context_bus is not None:
            plan = context_bus.get("plan") or context_bus.get("structured_plan")
        step_results = kwargs.get("step_results")
        if step_results is None and context_bus is not None:
            step_results = context_bus.get("step_results") or []
        final_answer = self._task_text(task, context_bus, kwargs)
        memory_context = kwargs.get("memory_context")
        if memory_context is None and context_bus is not None:
            memory_context = context_bus.compose_context()
        if plan is None:
            plan = type("Plan", (), {"steps": []})()
        critique = self.critic.review(
            user_input=kwargs.get("user_input", final_answer),
            memory_context=memory_context or "",
            plan=plan,
            step_results=step_results or [],
            final_answer=final_answer,
        )
        if context_bus is not None:
            context_bus.set("critique", critique)
            context_bus.publish("critique", critique, source=self.name)
            context_bus.add_agent_report(self.name, critique)
        return critique
