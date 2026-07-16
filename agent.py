import logging

import ollama

from conversation import Conversation
from conversation_summarizer import ConversationSummarizer
from memory import Memory
from memory_extractor import MemoryExtractor
from memory_validator import MemoryValidator
from normalizer import Normalizer
from parser import ToolParser
from prompts import create_system_prompt
from tool_executor import ToolExecutor
from tools import tool_manager


logger = logging.getLogger(__name__)


class Agent:


    def __init__(self, model="qwen2.5:7b"):

        self.model = model

        self.executor = ToolExecutor()
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

        response = ollama.chat(
            model=self.model,
            messages=self.conversation.get_messages()
        )

        answer = response["message"]["content"]

        logger.debug(
            "Model response: %s",
            answer
        )

        tool_call = self.parser.parse(
            answer
        )

        if tool_call and "tool" in tool_call:

            tool_name = tool_call["tool"]

            logger.info(
                "Tool recognized: %s",
                tool_name
            )

            if "input" in tool_call:
                tool_input = tool_call["input"]
            else:
                tool_input = {
                    key: value
                    for key, value in tool_call.items()
                    if key != "tool"
                }

            success, result = self.executor.execute(
                tool_name,
                tool_input
            )

            if not success:
                return result

            logger.info(
                "Tool result: %s",
                result
            )

            self.conversation.add_assistant(
                f"Ich habe das Werkzeug '{tool_name}' verwendet."
            )

            self.conversation.add_user(
                f"""
                Das Werkzeug wurde ausgeführt.

                Werkzeug:
                {tool_name}

                Ergebnis:
                {result}

                Beantworte jetzt die ursprüngliche Benutzeranfrage.
                Antworte nur mit normalem Text.
                Erzeuge kein JSON.
                """
            )

            final = ollama.chat(
                model=self.model,
                messages=self.conversation.get_messages()
            )

            final_answer = final["message"]["content"]

            self.conversation.add_assistant(
                final_answer
            )

            return final_answer


        self.conversation.add_assistant(
            answer
        )

        conversation_text = f"""
        User:
        {user_input}

        Assistant:
        {answer}
        """

        self.update_memory(
            conversation_text
        )

        return answer


    def update_memory(self, conversation_text):

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
