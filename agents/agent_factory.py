from __future__ import annotations

from typing import Any, Type

from agent_registry import AgentRegistry


class AgentFactory:
    def __init__(self, registry: AgentRegistry | None = None):
        self.registry = registry if registry is not None else AgentRegistry()


    def create(self, agent_cls: Type, /, *args, register: bool = True, **kwargs):
        agent = agent_cls(*args, **kwargs)
        if register:
            self.registry.register(agent)
        return agent


    def create_named(self, agent_name: str, agent_cls: Type, /, *args, **kwargs):
        agent = self.create(agent_cls, *args, **kwargs)
        if getattr(agent, "name", None) != agent_name:
            agent.name = agent_name
            self.registry.register(agent)
        return agent


    def build(self, mapping: dict[str, tuple[Type, tuple, dict[str, Any]]]):
        created = {}
        for name, (agent_cls, args, kwargs) in mapping.items():
            created[name] = self.create_named(name, agent_cls, *args, **kwargs)
        return created
