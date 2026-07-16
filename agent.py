import logging

import ollama

from conversation import Conversation
from conversation_summarizer import ConversationSummarizer
from critic import Critic
from execution_loop import ExecutionLoop
from memory import Memory
from memory_extractor import MemoryExtractor
from memory_validator import MemoryValidator
from normalizer import Normalizer
from parser import ToolParser
from planner import Planner
from prompts import create_system_prompt
from orchestrator import Orchestrator
from research.pipeline import ResearchPipeline
from tool_executor import ToolExecutor
from tools import tool_manager


logger = logging.getLogger(__name__)


class Agent:


    def __init__(self, model="qwen2.5:7b"):

        self.model = model
        self.parser = ToolParser()

        self.orchestrator = Orchestrator(
            model=model,
            planner_cls=Planner,
            critic_cls=Critic,
            execution_loop_cls=ExecutionLoop,
            research_pipeline_cls=ResearchPipeline,
            memory_cls=Memory,
            extractor_cls=MemoryExtractor,
            validator_cls=MemoryValidator,
            summarizer_cls=ConversationSummarizer,
            normalizer_cls=Normalizer,
            tool_executor_cls=ToolExecutor,
            tool_manager_obj=tool_manager,
        )

        self.executor = self.orchestrator.execution_loop.tool_executor
        self.planner = self.orchestrator.planner
        self.critic = self.orchestrator.critic
        self.memory = self.orchestrator.memory
        self.memory_extractor = self.orchestrator.extractor
        self.memory_validator = self.orchestrator.validator
        self.memory_summarizer = self.orchestrator.summarizer
        self.normalizer = self.orchestrator.normalizer
        self.research_pipeline = self.orchestrator.research_pipeline
        self.execution_loop = self.orchestrator.execution_loop
        self.system_prompt = self.orchestrator.conversation.get_messages()[0]["content"]
        self.conversation = self.orchestrator.conversation

        self.last_plan = self.orchestrator.last_plan
        self.last_execution = self.orchestrator.last_execution
        self.last_reflection = self.orchestrator.last_reflection
        self.last_research_result = self.orchestrator.last_research_result
        self.last_answer = self.orchestrator.last_answer


    def think(self, user_input):

        if user_input.startswith("memory test"):

            self.memory.save_fact(
                "test",
                "funktioniert",
                "ja",
                importance=5,
                confidence=0.9
            )

            return str(
                self.memory.get_all_facts()
            )


        orchestration = self.orchestrator.think(user_input)
        final_answer = orchestration.final_response
        plan = orchestration.plan
        execution = orchestration.context.get("execution", {}) if isinstance(orchestration.context, dict) else {}
        reflection = orchestration.context.get("reflection") if isinstance(orchestration.context, dict) else None
        if reflection is None:
            reflection = self.orchestrator.last_reflection

        self.last_plan = plan
        self.last_execution = execution
        self.last_reflection = reflection
        self.last_answer = final_answer
        self.last_research_result = self._extract_research_result(execution.get("step_results", []) if isinstance(execution, dict) else [])

        execution_text = self._format_execution_trace(
            user_input,
            final_answer,
            plan,
            execution.get("step_results", []) if isinstance(execution, dict) else [],
            reflection
        )

        self.update_memory(
            execution_text,
            reflection=reflection
        )

        return final_answer


    def _format_execution_trace(self, user_input, answer, plan, step_results, reflection=None):
        plan_lines = [
            f"- {index + 1}. {step.action}: {step.description}"
            for index, step in enumerate(plan.steps)
        ]
        result_lines = [
            f"- {item.get('action')}: {item.get('result')}"
            for item in step_results
        ]

        reflection_lines = []
        if reflection:
            reflection_lines = [
                f"- Verdict: {getattr(reflection, 'verdict', '')}",
                f"- Summary: {getattr(reflection, 'summary', '')}",
            ]
            for risk in getattr(reflection, 'risks', []) or []:
                reflection_lines.append(f"- Risk: {risk}")
            for improvement in getattr(reflection, 'improvements', []) or []:
                reflection_lines.append(f"- Improvement: {improvement}")

        return f"""
        User:
        {user_input}

        Plan goal:
        {plan.goal}

        Plan steps:
        {chr(10).join(plan_lines)}

        Step results:
        {chr(10).join(result_lines)}

        Reflection:
        {chr(10).join(reflection_lines)}

        Final answer:
        {answer}
        """


    def update_memory(self, conversation_text, reflection=None):

        memories = self.memory_extractor.extract(
            conversation_text
        )

        if not memories:
            summary = self.memory_summarizer.summarize(
                conversation_text,
                []
            )
            self._store_summary(summary)
            return

        normalized_memories = []
        for memory in memories:
            if not isinstance(memory, dict):
                continue
            if not memory.get("category") or not memory.get("key") or not memory.get("value"):
                continue
            try:
                normalized_memories.append(
                    self.normalizer.normalize_fact(
                        memory
                    )
                )
            except Exception:
                continue

        for memory in normalized_memories:

            validation = self.memory_validator.validate(
                memory,
                conversation_text
            )

            if not validation:
                continue

            if not validation.get(
                "approved",
                False
            ):
                logger.info(
                    "Memory rejected: %s",
                    memory
                )
                continue

            importance = validation.get(
                "importance",
                memory.get(
                    "importance",
                    5
                )
            )
            confidence = validation.get(
                "confidence",
                0.75
            )

            status = self.memory.save_fact(
                key=memory["key"],
                value=memory["value"],
                category=memory.get(
                    "category",
                    "general"
                ),
                importance=importance,
                confidence=confidence
            )

            logger.info(
                "Memory status: %s",
                status.get("status")
            )

        summary = self.memory_summarizer.summarize(
            conversation_text,
            normalized_memories
        )
        self._store_summary(summary)
        self._store_reflection(reflection)


    def _extract_research_result(self, step_results):
        for item in step_results:
            if item.get("action") in {"research", "research_pipeline"}:
                result = item.get("result")
                if isinstance(result, dict):
                    return result
        return None


    def _store_reflection(self, reflection):
        if not reflection:
            return

        if getattr(reflection, "summary", None) is None:
            return

        topic = "execution_reflection"
        payload = f"{getattr(reflection, 'verdict', 'warn')}: {reflection.summary}"

        if getattr(reflection, 'risks', None):
            payload += "\nRisks: " + "; ".join(reflection.risks)
        if getattr(reflection, 'improvements', None):
            payload += "\nImprovements: " + "; ".join(reflection.improvements)

        status = self.memory.save_summary(
            topic,
            payload,
            importance=5 if getattr(reflection, 'verdict', 'warn') == 'pass' else 6,
            confidence=getattr(reflection, 'confidence', 0.65)
        )

        logger.info(
            "Reflection status: %s",
            status.get("status")
        )


    def _store_summary(self, summary):
        if not summary:
            return

        summary = self.normalizer.normalize_summary(
            summary
        )

        if not summary.get("topic") or not summary.get("summary"):
            return

        if int(summary.get("importance", 0) or 0) <= 0:
            return

        status = self.memory.save_summary(
            summary["topic"],
            summary["summary"],
            importance=summary.get(
                "importance",
                5
            ),
            confidence=summary.get(
                "confidence",
                0.65
            )
        )

        logger.info(
            "Summary status: %s",
            status.get("status")
        )
