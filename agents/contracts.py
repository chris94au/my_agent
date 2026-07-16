from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class AgentTask:
    goal: str
    input_text: str = ""
    agent_names: list[str] = field(default_factory=list)
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RoutingDecision:
    task: str
    agents: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    parallel_groups: list[list[str]] = field(default_factory=list)
    confidence: float = 0.5
    priority: int = 0


@dataclass(slots=True)
class AgentOutcome:
    agent_name: str
    status: str
    output: Any = None
    errors: list[str] = field(default_factory=list)
    runtime_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrchestrationResult:
    task: str
    plan: Any = None
    outcomes: list[AgentOutcome] = field(default_factory=list)
    final_response: str = ""
    status: str = "ok"
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
