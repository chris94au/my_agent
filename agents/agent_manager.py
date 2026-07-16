from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from agent_registry import AgentRegistry
from .contracts import AgentOutcome


@dataclass(slots=True)
class ExecutionReport:
    outcomes: list[AgentOutcome] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class AgentManager:
    def __init__(self, registry: AgentRegistry | None = None):
        self.registry = registry if registry is not None else AgentRegistry()


    def register(self, agent):
        return self.registry.register(agent)


    def get(self, name: str):
        return self.registry.get(name)


    def list(self):
        return self.registry.list()


    def execute(self, name: str, context_bus, task: Any | None = None, **kwargs):
        agent = self.get(name)
        if agent is None:
            return AgentOutcome(agent_name=name, status="missing", output=None, errors=[f"Unknown agent: {name}"])

        start = perf_counter()
        try:
            output = agent.execute(context_bus, task=task, **kwargs)
            runtime_ms = (perf_counter() - start) * 1000.0
            outcome = AgentOutcome(agent_name=name, status="ok", output=output, runtime_ms=runtime_ms)
            context_bus.add_agent_report(name, output)
            context_bus.publish("agent_outcome", outcome, source=name)
            return outcome
        except Exception as exc:
            runtime_ms = (perf_counter() - start) * 1000.0
            outcome = AgentOutcome(agent_name=name, status="error", output=None, errors=[str(exc)], runtime_ms=runtime_ms)
            context_bus.add_agent_report(name, {"error": str(exc)})
            context_bus.publish("agent_error", outcome, source=name)
            return outcome
