from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from agents.base_agent import BaseAgent


@dataclass(slots=True)
class AgentRecord:
    agent: BaseAgent
    name: str
    role: str
    description: str
    version: str
    capabilities: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    priority: int = 0


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, AgentRecord] = {}


    def register(self, agent: BaseAgent):
        record = AgentRecord(
            agent=agent,
            name=agent.name,
            role=agent.role,
            description=agent.description,
            version=getattr(agent, "version", "1.0"),
            capabilities=list(getattr(agent, "capabilities", [])),
            allowed_tools=list(getattr(agent, "allowed_tools", [])),
            denied_tools=list(getattr(agent, "denied_tools", [])),
            priority=int(getattr(agent, "priority", 0)),
        )
        self._agents[record.name] = record
        return agent


    def unregister(self, name: str):
        return self._agents.pop(name, None)


    def get(self, name: str):
        record = self._agents.get(name)
        return record.agent if record else None


    def get_record(self, name: str):
        return self._agents.get(name)


    def list(self):
        return [record.agent for record in sorted(self._agents.values(), key=lambda item: (-item.priority, item.name))]


    def list_records(self):
        return [record for record in sorted(self._agents.values(), key=lambda item: (-item.priority, item.name))]


    def list_metadata(self):
        return [
            {
                "name": record.name,
                "role": record.role,
                "description": record.description,
                "version": record.version,
                "capabilities": list(record.capabilities),
                "allowed_tools": list(record.allowed_tools),
                "denied_tools": list(record.denied_tools),
                "priority": record.priority,
            }
            for record in self.list_records()
        ]


    def find_by_capability(self, capability: str):
        capability = str(capability).casefold()
        return [record.agent for record in self._agents.values() if any(capability == item.casefold() or capability in item.casefold() for item in record.capabilities)]


    def find_by_tool(self, tool_name: str):
        tool_name = str(tool_name).casefold()
        return [record.agent for record in self._agents.values() if any(tool_name == item.casefold() for item in record.allowed_tools)]


    def priorities(self):
        return {record.name: record.priority for record in self._agents.values()}


    def capabilities(self):
        return {record.name: list(record.capabilities) for record in self._agents.values()}


    def allowed_tools(self):
        return {record.name: list(record.allowed_tools) for record in self._agents.values()}


    def versions(self):
        return {record.name: record.version for record in self._agents.values()}


    def __contains__(self, name: str):
        return name in self._agents


    def __len__(self):
        return len(self._agents)
