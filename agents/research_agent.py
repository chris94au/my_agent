from __future__ import annotations

from dataclasses import asdict
from typing import Any

from memory import Memory
from research.pipeline import ResearchPipeline

from .base_agent import BaseAgent
from .contracts import AgentTask


class ResearchAgent(BaseAgent):
    def __init__(
        self,
        *,
        name: str = "research_agent",
        role: str = "research",
        description: str = "Führt Webrecherche, Quellenbewertung und Zitationsaufbau aus.",
        system_prompt: str = "",
        capabilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        version: str = "1.0",
        priority: int = 80,
        model: str = "qwen2.5:7b",
        memory: Memory | None = None,
        research_pipeline_cls=ResearchPipeline,
    ):
        super().__init__(
            name=name,
            role=role,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities or ["web research", "source ranking", "citation tracking"],
            allowed_tools=allowed_tools or ["web_search", "web_fetch", "read_url"],
            denied_tools=["filesystem:read", "filesystem:write", "scheduler"],
            version=version,
            priority=priority,
        )
        self.model = model
        self.memory = memory or Memory()
        self.pipeline = research_pipeline_cls(model=model, memory=self.memory)


    def _task_text(self, task: Any | None, context_bus, kwargs):
        if isinstance(task, AgentTask):
            return task.input_text or task.goal
        if isinstance(task, dict):
            for key in ("query", "input_text", "goal", "input", "message", "text"):
                value = task.get(key)
                if value:
                    return str(value)
        if task is not None:
            return str(task)
        for key in ("query", "user_input", "task"):
            value = kwargs.get(key)
            if value:
                return str(value)
        if context_bus is not None:
            shared = context_bus.get("user_input") if hasattr(context_bus, "get") else None
            if shared:
                return str(shared)
        return ""


    def execute(self, context_bus, task: Any | None = None, **kwargs):
        query = self._task_text(task, context_bus, kwargs)
        memory_context = kwargs.get("memory_context")
        if memory_context is None and context_bus is not None:
            memory_context = context_bus.compose_context()
        limit = int(kwargs.get("limit", 5))
        result = self.pipeline.run(query=query, memory_context=memory_context or "", limit=limit)
        payload = result.__dict__ if hasattr(result, "__dict__") else result
        if context_bus is not None:
            context_bus.set("research", payload)
            context_bus.add_source({"query": query, "sources_used": payload.get("sources_used", [])})
            context_bus.publish("research", payload, source=self.name)
            context_bus.add_agent_report(self.name, payload)
        return result
