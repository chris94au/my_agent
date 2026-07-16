import logging

import ollama

from planner import Plan


logger = logging.getLogger(__name__)


class ExecutionLoop:

    def __init__(self, model, tool_executor, tool_manager):
        self.model = model
        self.tool_executor = tool_executor
        self.tool_manager = tool_manager


    def _render_step_results(self, step_results):
        lines = []
        for index, item in enumerate(step_results, start=1):
            lines.append(
                f"Schritt {index} [{item.get('action')}]: {item.get('result')}"
            )
        return "\n".join(lines)


    def _synthesize_response(self, user_input, memory_context, plan, step_results):
        plan_text = []
        for index, step in enumerate(plan.steps, start=1):
            plan_text.append(
                f"{index}. {step.action} | {step.description}"
            )

        prompt = f"""
Du bist der Ausführungsmodus eines lokalen KI-Agenten.

Beantworte die ursprüngliche Anfrage auf Basis des Plans und der Ergebnisse.
Antworte in normalem Text und ohne JSON.

Benutzeranfrage:
{user_input}

Memory-Kontext:
{memory_context or ""}

Plan:
{chr(10).join(plan_text)}

Ergebnisse der Ausführung:
{self._render_step_results(step_results)}
"""

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        return response["message"]["content"]


    def run(self, user_input, memory_context, plan):
        step_results = []
        for step in plan.steps:
            logger.info(
                "Executing step: %s",
                step.action
            )

            if step.action in {"respond", "generate_response"}:
                result = self._synthesize_response(
                    user_input,
                    memory_context,
                    plan,
                    step_results
                )
                step_results.append(
                    {
                        "action": step.action,
                        "input": step.input,
                        "result": result,
                        "status": "ok"
                    }
                )
                return {
                    "answer": result,
                    "step_results": step_results,
                    "plan": plan
                }

            if step.action in {"summarize", "analyze", "reflect", "review"}:
                result = self._synthesize_response(
                    user_input,
                    memory_context,
                    plan,
                    step_results
                )
                step_results.append(
                    {
                        "action": step.action,
                        "input": step.input,
                        "result": result,
                        "status": "ok"
                    }
                )
                continue

            success, result = self.tool_executor.execute(
                step.action,
                step.input
            )
            step_results.append(
                {
                    "action": step.action,
                    "input": step.input,
                    "result": result,
                    "status": "ok" if success else "error"
                }
            )

            if not success:
                logger.warning(
                    "Tool step failed: %s",
                    result
                )
                continue

        final_answer = self._synthesize_response(
            user_input,
            memory_context,
            plan,
            step_results
        )
        return {
            "answer": final_answer,
            "step_results": step_results,
            "plan": plan
        }
