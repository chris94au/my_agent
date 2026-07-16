import json
import logging
import re
from dataclasses import dataclass, field

import ollama


logger = logging.getLogger(__name__)


SPECIAL_ACTIONS = {
    "respond",
    "generate_response",
    "summarize",
    "analyze",
    "reflect",
    "review"
}


@dataclass
class PlanStep:
    action: str
    input: object = None
    description: str = ""
    tool: str = ""


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    valid: bool = True
    validation_errors: list[str] = field(default_factory=list)


class Planner:

    def __init__(self, model="qwen2.5:7b", max_steps=8):
        self.model = model
        self.max_steps = max_steps


    def _build_prompt(self, user_input, memory_context, tool_descriptions):
        return f"""
Du bist ein Planner für einen lokalen KI-Agenten.

Deine Aufgabe ist es, eine Benutzeranfrage in geordnete Ausführungsschritte zu zerlegen.
Wenn die Aufgabe einfach ist, genügt ein einzelner Schritt.
Wenn sie komplex ist, dekomponiere sie in klar geordnete Teilschritte.

Verfügbare Werkzeuge:
{tool_descriptions}

Relevanter Memory-Kontext:
{memory_context or ""}

Benutzeranfrage:
{user_input}

Antworte ausschließlich mit JSON.

Schema:
{{
  "goal": "kurzes Hauptziel",
  "steps": [
    {{
      "action": "tool_name_oder_summarize_oder_analyze_oder_respond",
      "input": "optional oder Objekt",
      "description": "kurze Beschreibung"
    }}
  ]
}}

Regeln:
- Nutze nur Werkzeuge, die in der Liste verfügbar sind.
- Ordne die Schritte logisch.
- Maximal {self.max_steps} Schritte.
- Das letzte Ziel soll immer zu einer Benutzerantwort führen.
- Wenn kein Tool nötig ist, plane mindestens einen respond-Schritt.
"""


    def _extract_json(self, text):
        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )
        if not match:
            return None

        try:
            return json.loads(
                match.group()
            )
        except json.JSONDecodeError:
            return None


    def _fallback_plan(self, user_input, memory_context):
        lowered = user_input.casefold()
        steps = []
        goal = user_input.strip()[:120] or "Aufgabe ausführen"

        if any(token in lowered for token in ("analys", "fasse", "zusammen", "datei", "inhalt")):
            file_match = re.search(r"([\w./-]+\.(?:txt|md|py|json|csv|log|yaml|yml))", user_input, re.I)
            if file_match:
                steps.append(
                    PlanStep(
                        action="read_file",
                        input=file_match.group(1),
                        description="Datei lesen",
                        tool="read_file"
                    )
                )
            steps.extend(
                [
                    PlanStep(
                        action="analyze",
                        description="Inhalt analysieren"
                    ),
                    PlanStep(
                        action="summarize",
                        description="Wichtigste Punkte zusammenfassen"
                    ),
                    PlanStep(
                        action="respond",
                        description="Antwort formulieren"
                    )
                ]
            )
        elif any(token in lowered for token in ("vergleic", "unterschied", "gegenüber", "vs")):
            steps.extend(
                [
                    PlanStep(action="analyze", description="Aspekte herausarbeiten"),
                    PlanStep(action="respond", description="Vergleich erklären")
                ]
            )
        else:
            steps.append(
                PlanStep(
                    action="respond",
                    description="Antwort formulieren"
                )
            )

        return Plan(
            goal=goal,
            steps=steps,
            raw={"goal": goal, "steps": [step.__dict__ for step in steps]},
            valid=True,
            validation_errors=[]
        )


    def _validate_plan(self, data, available_tools=None):
        errors = []
        if not isinstance(data, dict):
            return self._fallback_plan("", "")

        goal = str(data.get("goal", "")).strip()
        steps_data = data.get("steps", [])

        if not goal:
            errors.append("goal missing")

        if not isinstance(steps_data, list) or not steps_data:
            errors.append("steps missing")

        steps = []
        available_tool_names = set(available_tools or [])

        for raw_step in steps_data[: self.max_steps]:
            if not isinstance(raw_step, dict):
                errors.append("step not an object")
                continue

            action = str(raw_step.get("action", "")).strip()
            if not action:
                errors.append("step action missing")
                continue

            if available_tool_names and action not in SPECIAL_ACTIONS and action not in available_tool_names:
                errors.append(f"unknown tool action: {action}")
                continue

            steps.append(
                PlanStep(
                    action=action,
                    input=raw_step.get("input"),
                    description=str(raw_step.get("description", "")).strip(),
                    tool=raw_step.get("tool", action if action not in SPECIAL_ACTIONS else "")
                )
            )

        if not steps:
            errors.append("no valid steps")

        return Plan(
            goal=goal or "Aufgabe ausführen",
            steps=steps,
            raw=data,
            valid=not errors,
            validation_errors=errors
        )


    def plan(self, user_input, memory_context="", tool_descriptions="", available_tools=None):
        prompt = self._build_prompt(
            user_input,
            memory_context,
            tool_descriptions
        )

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            text = response["message"]["content"]
            plan_data = self._extract_json(text)
            if plan_data is None:
                raise ValueError("Planner output was not valid JSON")

            plan = self._validate_plan(
                plan_data,
                available_tools=available_tools
            )
            if not plan.valid:
                logger.warning(
                    "Planner validation failed (%s); using fallback plan",
                    ", ".join(plan.validation_errors)
                )
                return self._fallback_plan(user_input, memory_context)

            return plan

        except Exception as exc:
            logger.warning(
                "Planner fallback due to error: %s",
                exc
            )
            return self._fallback_plan(user_input, memory_context)
