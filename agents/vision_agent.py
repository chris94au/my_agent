from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from .contracts import AgentTask


class VisionAgent(BaseAgent):
    def __init__(
        self,
        *,
        name: str = "vision_agent",
        role: str = "vision",
        description: str = "Analysiert Bilder, OCR, Screenshots und Diagramme.",
        system_prompt: str = "",
        capabilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        version: str = "1.0",
        priority: int = 65,
    ):
        super().__init__(
            name=name,
            role=role,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities or ["image analysis", "ocr", "screenshots", "diagrams"],
            allowed_tools=allowed_tools or [],
            denied_tools=["filesystem:write", "scheduler", "sensitive_actions"],
            version=version,
            priority=priority,
        )


    def _task_payload(self, task: Any | None, context_bus, kwargs):
        if isinstance(task, AgentTask):
            return dict(task.metadata)
        if isinstance(task, dict):
            return dict(task)
        payload = {}
        payload.update(kwargs)
        if context_bus is not None:
            shared = context_bus.get("vision_input") if hasattr(context_bus, "get") else None
            if shared and isinstance(shared, dict):
                payload.update(shared)
        return payload


    def execute(self, context_bus, task: Any | None = None, **kwargs):
        payload = self._task_payload(task, context_bus, kwargs)
        result = {
            "image_path": payload.get("image_path"),
            "description": payload.get("description") or payload.get("image_description") or "Bildanalyse nicht voll angebunden",
            "ocr_text": payload.get("ocr_text", ""),
            "diagram_notes": payload.get("diagram_notes", []),
            "status": "ok" if payload else "missing_input",
        }
        if context_bus is not None:
            context_bus.set("vision", result)
            context_bus.publish("vision", result, source=self.name)
            context_bus.add_agent_report(self.name, result)
        return result
