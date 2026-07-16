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
from tool_executor import ToolExecutor
from tools import tool_manager


logger = logging.getLogger(__name__)


class Agent:


    def __init__(self, model="qwen2.5:7b"):

        self.model = model

        self.executor = ToolExecutor()
        self.planner = Planner(model=model)
        self.critic = Critic(model=model)
        self.execution_loop = ExecutionLoop(
            model=model,
            tool_executor=self.executor,
            tool_manager=tool_manager,
            critic=self.critic
        )
        self.parser = ToolParser()

        self.memory = Memory()
        self.memory_extractor = MemoryExtractor()
        self.memory_validator = MemoryValidator()
        self.memory_summarizer = ConversationSummarizer()
        self.normalizer = Normalizer()

        self.system_prompt = create_system_prompt(
            tool_manager
        )

        self.conversation = Conversation(
            self.system_prompt
        )


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


        self.conversation.add_user(
            user_input
        )

        memory_context = self.memory.get_semantic_context(
            user_input
        )
        self.conversation.add_system(
            memory_context
        )

        plan = self.planner.plan(
            user_input=user_input,
            memory_context=memory_context,
            tool_descriptions=tool_manager.get_descriptions(),
            available_tools=[
                tool.name
                for tool in tool_manager.list_tools()
            ]
        )

        logger.info(
            "Planner goal: %s",
            plan.goal
        )

        execution = self.execution_loop.run(
            user_input=user_input,
            memory_context=memory_context,
            plan=plan
        )

        final_answer = execution["answer"]
        reflection = execution.get("reflection")

        self.conversation.add_assistant(
            final_answer
        )

        execution_text = self._format_execution_trace(
            user_input,
            final_answer,
            plan,
            execution.get("step_results", []),
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

        memories = [
            self.normalizer.normalize_fact(
                memory
            )
            for memory in memories
        ]

        for memory in memories:

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
            memories
        )
        self._store_summary(summary)
        self._store_reflection(reflection)


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
