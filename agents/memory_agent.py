from __future__ import annotations

from typing import Any

from conversation_summarizer import ConversationSummarizer
from memory import Memory
from memory_extractor import MemoryExtractor
from memory_validator import MemoryValidator
from normalizer import Normalizer

from .base_agent import BaseAgent
from .contracts import AgentTask


class MemoryAgent(BaseAgent):
    def __init__(
        self,
        *,
        name: str = "memory_agent",
        role: str = "memory",
        description: str = "Verwaltet Retrieval, Normalisierung, Validierung, Konsolidierung und Archivierung von Memory.",
        system_prompt: str = "",
        capabilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        version: str = "1.0",
        priority: int = 70,
        memory: Memory | None = None,
        extractor_cls=MemoryExtractor,
        validator_cls=MemoryValidator,
        summarizer_cls=ConversationSummarizer,
        normalizer_cls=Normalizer,
    ):
        super().__init__(
            name=name,
            role=role,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities or ["retrieval", "normalization", "consolidation", "confidence", "importance"],
            allowed_tools=allowed_tools or [],
            denied_tools=["filesystem:write", "scheduler", "sensitive_actions"],
            version=version,
            priority=priority,
        )
        self.memory = memory or Memory()
        self.extractor = extractor_cls()
        self.validator = validator_cls()
        self.summarizer = summarizer_cls()
        self.normalizer = normalizer_cls()


    def _task_text(self, task: Any | None, context_bus, kwargs):
        if isinstance(task, AgentTask):
            return task.input_text or task.goal
        if isinstance(task, dict):
            for key in ("text", "conversation", "query", "goal", "input_text", "input"):
                value = task.get(key)
                if value:
                    return str(value)
        if task is not None:
            return str(task)
        for key in ("text", "conversation", "query", "user_input", "task"):
            value = kwargs.get(key)
            if value:
                return str(value)
        if context_bus is not None:
            shared = context_bus.get("user_input") if hasattr(context_bus, "get") else None
            if shared:
                return str(shared)
        return ""


    def retrieve(self, query: str):
        facts = self.memory.get_all_facts()
        summaries = self.memory.get_all_summaries()
        relevant = self.memory.get_semantic_context(query)
        return {
            "query": query,
            "facts": facts,
            "summaries": summaries,
            "relevant": relevant,
        }


    def consolidate(self, conversation_text: str):
        memories = self.extractor.extract(conversation_text)
        if not memories:
            summary = self.summarizer.summarize(conversation_text, [])
            self._store_summary(summary)
            return {"type": "summary", "summary": summary}

        normalized = [self.normalizer.normalize_fact(memory) for memory in memories]
        stored = []
        for memory_item in normalized:
            validation = self.validator.validate(memory_item, conversation_text)
            if not validation or not validation.get("approved", False):
                continue
            importance = validation.get("importance", memory_item.get("importance", 5))
            confidence = validation.get("confidence", memory_item.get("confidence", 0.75))
            fact_result = self.memory.save_fact(
                memory_item["category"],
                memory_item["key"],
                memory_item["value"],
                importance=importance,
                confidence=confidence,
            )
            stored.append({"type": "fact", "result": fact_result})

        summary = self.summarizer.summarize(conversation_text, normalized)
        self._store_summary(summary)
        return {"type": "consolidated", "facts": stored, "summary": summary}


    def _store_summary(self, summary):
        if not summary:
            return None
        topic = summary.get("topic", "execution_reflection")
        text = summary.get("summary", "")
        importance = summary.get("importance", 5)
        confidence = summary.get("confidence", 0.7)
        return self.memory.save_summary(topic, text, importance=importance, confidence=confidence)


    def execute(self, context_bus, task: Any | None = None, **kwargs):
        text = self._task_text(task, context_bus, kwargs)
        operation = kwargs.get("operation")
        if isinstance(task, dict):
            operation = task.get("operation", operation)
        operation = str(operation or "retrieve").casefold()

        if operation in {"consolidate", "store", "archive"}:
            result = self.consolidate(text)
        else:
            result = self.retrieve(text)

        if context_bus is not None:
            context_bus.set("memory", result)
            context_bus.set_memory_context(result.get("relevant", result))
            context_bus.publish("memory", result, source=self.name)
            context_bus.add_agent_report(self.name, result)
        return result
