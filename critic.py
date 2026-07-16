import json
import logging
import re
from dataclasses import dataclass, field

import ollama


logger = logging.getLogger(__name__)


@dataclass
class Critique:
    verdict: str
    summary: str
    risks: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    confidence: float = 0.5
    should_retry: bool = False
    raw: dict = field(default_factory=dict)
    valid: bool = True
    validation_errors: list[str] = field(default_factory=list)


class Critic:

    def __init__(self, model="qwen2.5:7b"):
        self.model = model


    def _build_prompt(self, user_input, memory_context, plan, step_results, final_answer):
        plan_lines = []
        for index, step in enumerate(plan.steps, start=1):
            plan_lines.append(
                f"{index}. {step.action} | {step.description} | input={step.input}"
            )

        step_lines = []
        for index, item in enumerate(step_results, start=1):
            step_lines.append(
                f"{index}. {item.get('action')} | {item.get('status')} | {item.get('result')}"
            )

        return f"""
Du bist ein kritischer Reviewer für einen lokalen KI-Agenten.

Analysiere den Plan, die Schritte und die Antwort auf Qualität, Vollständigkeit,
Risiken und mögliche Verbesserungen.
Nutze den Memory-Kontext, um zu prüfen, ob die Antwort zum Nutzer passt.

Antworte ausschließlich als JSON mit diesem Schema:
{{
  "verdict": "pass|warn|fail",
  "summary": "kurze zusammenfassende Bewertung",
  "risks": ["..."],
  "improvements": ["..."],
  "confidence": 0.0,
  "should_retry": false
}}

Benutzeranfrage:
{user_input}

Memory-Kontext:
{memory_context or ""}

Plan:
{chr(10).join(plan_lines)}

Schritt-Ergebnisse:
{chr(10).join(step_lines)}

Finale Antwort:
{final_answer}
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
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None


    def _fallback(self, user_input, step_results, final_answer):
        failed_steps = [
            item for item in step_results if item.get("status") == "error"
        ]
        verdict = "fail" if failed_steps else "pass"
        risks = []
        if failed_steps:
            risks.append("Mindestens ein Tool-Schritt ist fehlgeschlagen")

        improvements = []
        if failed_steps:
            improvements.append("Fehlgeschlagene Tools vor der Antwort erneut prüfen")

        summary = final_answer if final_answer else "Die Ausführung wurde reflektiert."

        return Critique(
            verdict=verdict,
            summary=summary[:240],
            risks=risks,
            improvements=improvements,
            confidence=0.6 if failed_steps else 0.72,
            should_retry=bool(failed_steps),
            raw={
                "verdict": verdict,
                "summary": summary[:240],
                "risks": risks,
                "improvements": improvements,
                "confidence": 0.6 if failed_steps else 0.72,
                "should_retry": bool(failed_steps),
            },
            valid=True,
            validation_errors=[]
        )


    def _validate(self, data, final_answer):
        if not isinstance(data, dict):
            return self._fallback("", [], final_answer)

        errors = []
        verdict = str(data.get("verdict", "")).strip().casefold()
        if verdict not in {"pass", "warn", "fail"}:
            errors.append("verdict invalid")
            verdict = "warn"

        summary = str(data.get("summary", "")).strip() or final_answer or "Ausführung reflektiert."
        risks = data.get("risks", [])
        improvements = data.get("improvements", [])

        if not isinstance(risks, list):
            errors.append("risks invalid")
            risks = []
        if not isinstance(improvements, list):
            errors.append("improvements invalid")
            improvements = []

        try:
            confidence = float(data.get("confidence", 0.5))
        except Exception:
            errors.append("confidence invalid")
            confidence = 0.5

        should_retry = bool(data.get("should_retry", False))

        return Critique(
            verdict=verdict,
            summary=summary[:400],
            risks=[str(item)[:160] for item in risks[:5]],
            improvements=[str(item)[:160] for item in improvements[:5]],
            confidence=max(0.0, min(1.0, confidence)),
            should_retry=should_retry,
            raw=data,
            valid=not errors,
            validation_errors=errors
        )


    def review(self, user_input, memory_context, plan, step_results, final_answer):
        prompt = self._build_prompt(
            user_input,
            memory_context,
            plan,
            step_results,
            final_answer
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
            critique_data = self._extract_json(text)
            if critique_data is None:
                raise ValueError("Critic output was not valid JSON")
            critique = self._validate(critique_data, final_answer)
            if not critique.valid:
                logger.warning(
                    "Critic validation failed (%s); using fallback",
                    ", ".join(critique.validation_errors)
                )
                return self._fallback(user_input, step_results, final_answer)
            return critique
        except Exception as exc:
            logger.warning(
                "Critic fallback due to error: %s",
                exc
            )
            return self._fallback(user_input, step_results, final_answer)
