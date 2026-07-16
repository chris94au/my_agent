from __future__ import annotations

from dataclasses import asdict
from typing import Any

from agent_router import AgentRouter
from planner import Planner

from .base_agent import BaseAgent
from .contracts import AgentTask


class PlannerAgent(BaseAgent):
    def __init__(
        self,
        *,
        name: str = "planner_agent",
        role: str = "planner",
        description: str = "Zerlegt Aufgaben und wählt geeignete Agenten aus.",
        system_prompt: str = "",
        capabilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        version: str = "1.0",
        priority: int = 100,
        model: str = "qwen2.5:7b",
        planner_cls=Planner,
        router: AgentRouter | None = None,
    ):
        super().__init__(
            name=name,
            role=role,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities or ["task decomposition", "agent selection", "planning"],
            allowed_tools=allowed_tools or [],
            version=version,
            priority=priority,
        )
        self.model = model
        self.router = router or AgentRouter()
        self.planner = planner_cls(model=model)


    def _task_text(self, task: Any | None, context_bus, kwargs):
        if isinstance(task, AgentTask):
            return task.input_text or task.goal
        if isinstance(task, dict):
            for key in ("input_text", "goal", "input", "query", "message", "text"):
                value = task.get(key)
                if value:
                    return str(value)
        if task is not None:
            return str(task)
        for key in ("user_input", "task", "query"):
            value = kwargs.get(key)
            if value:
                return str(value)
        if context_bus is not None:
            shared = context_bus.get("user_input") if hasattr(context_bus, "get") else None
            if shared:
                return str(shared)
        return ""


    def execute(self, context_bus, task: Any | None = None, **kwargs):
        text = self._task_text(task, context_bus, kwargs)
        memory_context = kwargs.get("memory_context")
        if memory_context is None and context_bus is not None:
            memory_context = context_bus.compose_context()
        tool_descriptions = kwargs.get("tool_descriptions", "")
        available_tools = kwargs.get("available_tools")
        plan = self.planner.plan(
            user_input=text,
            memory_context=memory_context or "",
            tool_descriptions=tool_descriptions,
            available_tools=available_tools,
        )
        selected_agents = kwargs.get("selected_agents") or self.router.suggest_agents(text, context_bus=context_bus)
        structured_plan = {
            "goal": plan.goal,
            "agents": selected_agents,
            "steps": [
                step.description or step.action for step in plan.steps
            ],
            "raw": plan.raw,
            "valid": plan.valid,
            "validation_errors": list(plan.validation_errors),
        }
        if context_bus is not None:
            context_bus.set("plan", structured_plan)
            context_bus.set("planned_agents", list(selected_agents))
            context_bus.publish("plan", structured_plan, source=self.name)
            context_bus.add_agent_report(self.name, structured_plan)
        return plan
