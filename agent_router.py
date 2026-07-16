from __future__ import annotations

from dataclasses import asdict
from typing import Any

from agent_registry import AgentRegistry
from agents.contracts import RoutingDecision


class AgentRouter:
    def __init__(self, registry: AgentRegistry | None = None):
        self.registry = registry if registry is not None else AgentRegistry()


    def _text(self, task: Any, context_bus=None):
        parts = []
        if isinstance(task, dict):
            for key in ("goal", "input_text", "input", "query", "message", "text"):
                value = task.get(key)
                if value:
                    parts.append(str(value))
        elif task is not None:
            parts.append(str(task))
        if context_bus is not None:
            memory_context = context_bus.get_memory_context() if hasattr(context_bus, "get_memory_context") else {}
            if memory_context:
                parts.append(str(memory_context))
            shared = context_bus.get("task", None) if hasattr(context_bus, "get") else None
            if shared:
                parts.append(str(shared))
        return " ".join(parts).strip().casefold()


    def _default_agents(self, text: str):
        agents = ["planner_agent", "critic_agent"]
        reasons = ["planen und validieren"]
        parallel_groups: list[list[str]] = []

        coding_terms = ("code", "python-programm", "python programm", "refactor", "test", "bug", "implement", "funktion", "programm", "script", "skript")
        research_terms = ("research", "recherch", "quelle", "quellen", "compare", "vergle", "aktuell", "forschung")
        memory_terms = ("merke", "remember", "memory", "vorlieben", "bevorzug", "mag ich", "passt zu mir", "zu mir")
        knowledge_terms = ("dokument", "wissen", "rag", "knowledge", "datei", "handbuch", "wiki")
        vision_terms = ("bild", "image", "screenshot", "diagramm", "ocr", "foto", "scan")
        task_terms = ("task", "aufgabe", "plan", "scheduler", "termin", "resume", "priority")

        if any(term in text for term in vision_terms):
            agents = ["vision_agent", "knowledge_agent", "critic_agent"]
            reasons.append("Bildanalyse erkannt")
            return agents, reasons, parallel_groups

        if any(term in text for term in coding_terms):
            agents = ["planner_agent", "coding_agent", "critic_agent"]
            reasons.append("Codeaufgabe erkannt")
            return agents, reasons, parallel_groups

        if any(term in text for term in research_terms):
            agents = ["planner_agent", "research_agent", "knowledge_agent", "critic_agent"]
            reasons.append("Rechercheaufgabe erkannt")
            parallel_groups.append(["research_agent", "knowledge_agent"])
            return agents, reasons, parallel_groups

        if any(term in text for term in memory_terms):
            agents = ["planner_agent", "memory_agent", "knowledge_agent", "research_agent", "critic_agent"]
            reasons.append("Persönlichkeits- oder Memory-Kontext erkannt")
            parallel_groups.append(["memory_agent", "knowledge_agent"])
            return agents, reasons, parallel_groups

        if any(term in text for term in knowledge_terms):
            agents = ["planner_agent", "knowledge_agent", "critic_agent"]
            reasons.append("Wissensabruf erkannt")
            return agents, reasons, parallel_groups

        if any(term in text for term in task_terms):
            agents = ["planner_agent", "task_agent", "critic_agent"]
            reasons.append("Langzeitaufgabe erkannt")
            return agents, reasons, parallel_groups

        return agents, reasons, parallel_groups


    def route(self, task: Any, context_bus=None, plan: Any | None = None):
        text = self._text(task, context_bus)
        agents, reasons, parallel_groups = self._default_agents(text)

        if plan is not None:
            plan_agents = []
            if isinstance(plan, dict):
                plan_agents = list(plan.get("agents", []))
            else:
                plan_agents = list(getattr(plan, "agents", []) or [])
            for agent_name in plan_agents:
                if agent_name not in agents:
                    agents.insert(-1 if agents and agents[-1] == "critic_agent" else len(agents), agent_name)
                    reasons.append(f"plan selects {agent_name}")

        if self.registry and len(self.registry) > 0:
            available = {record.name for record in self.registry.list_records()}
            agents = [name for name in agents if name in available]

        priority = 0
        if any(name in agents for name in ("research_agent", "coding_agent", "vision_agent")):
            priority = 1

        confidence = 0.75 if len(agents) > 2 else 0.6
        decision = RoutingDecision(
            task=text,
            agents=agents,
            reasons=reasons,
            parallel_groups=parallel_groups,
            confidence=confidence,
            priority=priority,
        )
        return decision


    def suggest_agents(self, task: Any, context_bus=None):
        return self.route(task, context_bus=context_bus).agents
