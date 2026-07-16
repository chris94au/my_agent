from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class PermissionPolicy:
    allowed_tools: set[str] = field(default_factory=set)
    denied_tools: set[str] = field(default_factory=set)
    allow_all: bool = False


    @classmethod
    def from_lists(
        cls,
        allowed_tools: Iterable[str] | None = None,
        denied_tools: Iterable[str] | None = None,
        allow_all: bool = False,
    ):
        return cls(
            allowed_tools=set(allowed_tools or []),
            denied_tools=set(denied_tools or []),
            allow_all=allow_all,
        )


    def permits_tool(self, tool_name: str) -> bool:
        tool_name = str(tool_name)
        if tool_name in self.denied_tools:
            return False
        if self.allow_all:
            return True
        if not self.allowed_tools:
            return True
        return tool_name in self.allowed_tools or "*" in self.allowed_tools


    def merged(self, *, allowed_tools: Iterable[str] | None = None, denied_tools: Iterable[str] | None = None, allow_all: bool | None = None):
        return PermissionPolicy(
            allowed_tools=set(allowed_tools or self.allowed_tools),
            denied_tools=set(denied_tools or self.denied_tools),
            allow_all=self.allow_all if allow_all is None else allow_all,
        )
