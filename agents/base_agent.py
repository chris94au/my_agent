from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .permissions import PermissionPolicy


@dataclass(slots=True)
class AgentMetadata:
    name: str
    role: str
    description: str
    system_prompt: str = ""
    capabilities: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    version: str = "1.0"
    priority: int = 0


class BaseAgent(ABC):
    def __init__(
        self,
        *,
        name: str,
        role: str,
        description: str,
        system_prompt: str = "",
        capabilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        denied_tools: list[str] | None = None,
        version: str = "1.0",
        priority: int = 0,
        permissions: PermissionPolicy | None = None,
    ):
        self.name = str(name)
        self.role = str(role)
        self.description = str(description)
        self.system_prompt = str(system_prompt)
        self.capabilities = list(capabilities or [])
        self.allowed_tools = list(allowed_tools or [])
        self.denied_tools = list(denied_tools or [])
        self.version = str(version)
        self.priority = int(priority)
        self.permissions = permissions or PermissionPolicy.from_lists(
            allowed_tools=self.allowed_tools,
            denied_tools=self.denied_tools,
        )


    def describe(self) -> AgentMetadata:
        return AgentMetadata(
            name=self.name,
            role=self.role,
            description=self.description,
            system_prompt=self.system_prompt,
            capabilities=list(self.capabilities),
            allowed_tools=list(self.allowed_tools),
            denied_tools=list(self.denied_tools),
            version=self.version,
            priority=self.priority,
        )


    def can_use_tool(self, tool_name: str) -> bool:
        return self.permissions.permits_tool(tool_name)


    def supports(self, capability: str) -> bool:
        capability = str(capability).casefold()
        return any(capability == item.casefold() or capability in item.casefold() for item in self.capabilities)


    @abstractmethod
    def execute(self, context_bus, task: Any | None = None, **kwargs):
        raise NotImplementedError
