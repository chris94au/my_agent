from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EvaluationMetrics:
    agent_selection: float = 0.0
    plan_quality: float = 0.0
    communication_quality: float = 0.0
    runtime_quality: float = 0.0
    error_rate: float = 0.0
    tool_usage: float = 0.0
    total: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EvaluationResult:
    task: str
    metrics: EvaluationMetrics
    details: dict[str, Any] = field(default_factory=dict)


class EvaluationFramework:
    def evaluate_orchestration(self, orchestration_result, *, runtime_ms: float | None = None):
        context = getattr(orchestration_result, "context", {}) or {}
        plan = getattr(orchestration_result, "plan", None)
        route = context.get("route_decision") or {}
        selected_agents = list(route.get("agents", []) or [])
        shared = context.get("shared", {}) or {}
        agent_reports = context.get("agent_reports", {}) or {}
        tool_results = context.get("tool_results", []) or []
        step_results = context.get("step_results", []) or []
        events = context.get("events", []) or []

        metrics = EvaluationMetrics()
        metrics.agent_selection = self._score_agent_selection(selected_agents, plan, route)
        metrics.plan_quality = self._score_plan_quality(plan)
        metrics.communication_quality = self._score_communication_quality(agent_reports, events, shared)
        metrics.runtime_quality = self._score_runtime_quality(runtime_ms)
        metrics.error_rate = self._score_error_rate(step_results, agent_reports, events)
        metrics.tool_usage = self._score_tool_usage(tool_results, step_results)
        metrics.total = round(
            (metrics.agent_selection + metrics.plan_quality + metrics.communication_quality + metrics.runtime_quality + metrics.tool_usage)
            / 5.0
            * (1.0 - min(metrics.error_rate, 1.0) * 0.4),
            3,
        )
        metrics.notes = self._build_notes(metrics)
        return EvaluationResult(task=getattr(orchestration_result, "task", ""), metrics=metrics, details={"route": route, "selected_agents": selected_agents})


    def _score_agent_selection(self, selected_agents, plan, route):
        if not selected_agents:
            return 0.0
        score = 0.5
        if "planner_agent" in selected_agents:
            score += 0.15
        if "critic_agent" in selected_agents:
            score += 0.15
        if any(name in selected_agents for name in ("research_agent", "coding_agent", "memory_agent", "knowledge_agent", "vision_agent", "task_agent")):
            score += 0.2
        if getattr(plan, "valid", True):
            score += 0.05
        if route.get("confidence", 0) >= 0.7:
            score += 0.05
        return min(score, 1.0)


    def _score_plan_quality(self, plan):
        if plan is None:
            return 0.0
        score = 0.0
        if getattr(plan, "valid", False):
            score += 0.4
        steps = getattr(plan, "steps", []) or []
        score += min(len(steps) / 4.0, 0.4)
        if not getattr(plan, "validation_errors", []):
            score += 0.2
        return min(score, 1.0)


    def _score_communication_quality(self, agent_reports, events, shared):
        report_count = sum(len(reports) for reports in agent_reports.values()) if isinstance(agent_reports, dict) else 0
        event_count = len(events) if isinstance(events, list) else 0
        shared_count = len(shared) if isinstance(shared, dict) else 0
        score = min(report_count / 6.0, 0.4) + min(event_count / 10.0, 0.4) + min(shared_count / 8.0, 0.2)
        return min(score, 1.0)


    def _score_runtime_quality(self, runtime_ms):
        if runtime_ms is None:
            return 0.5
        if runtime_ms <= 1000:
            return 1.0
        if runtime_ms <= 3000:
            return 0.8
        if runtime_ms <= 8000:
            return 0.6
        return 0.4


    def _score_error_rate(self, step_results, agent_reports, events):
        error_count = 0
        total = 0
        for item in step_results or []:
            total += 1
            if item.get("status") == "error":
                error_count += 1
        for reports in (agent_reports or {}).values():
            for report in reports:
                total += 1
                if isinstance(report, dict) and report.get("error"):
                    error_count += 1
        for event in events or []:
            total += 1
            if event.get("kind") in {"agent_error", "tool_error"}:
                error_count += 1
        return (error_count / total) if total else 0.0


    def _score_tool_usage(self, tool_results, step_results):
        used = len(tool_results or []) + sum(1 for item in (step_results or []) if item.get("status") == "ok" and item.get("action") not in {"respond", "analyze", "summarize", "reflect", "review"})
        return min(used / 4.0, 1.0)


    def _build_notes(self, metrics: EvaluationMetrics):
        notes = []
        if metrics.error_rate > 0:
            notes.append("Errors observed in execution or communication.")
        if metrics.tool_usage == 0:
            notes.append("No tool usage recorded.")
        if metrics.communication_quality < 0.4:
            notes.append("Agent communication is sparse.")
        return notes
