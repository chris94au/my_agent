from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from .contracts import AgentTask


class KnowledgeAgent(BaseAgent):
    def __init__(
        self,
        *,
        name: str = "knowledge_agent",
        role: str = "knowledge",
        description: str = "Führt RAG, Dokumentensuche und Wissensabruf aus.",
        system_prompt: str = "",
        capabilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        version: str = "1.0",
        priority: int = 60,
        knowledge_store: Any | None = None,
    ):
        super().__init__(
            name=name,
            role=role,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities or ["rag", "document search", "knowledge retrieval", "source evaluation"],
            allowed_tools=allowed_tools or [],
            denied_tools=["filesystem:write", "scheduler", "sensitive_actions"],
            version=version,
            priority=priority,
        )
        self.knowledge_store = knowledge_store


    def _task_text(self, task: Any | None, context_bus, kwargs):
        if isinstance(task, AgentTask):
            return task.input_text or task.goal
        if isinstance(task, dict):
            for key in ("query", "input_text", "goal", "input", "message", "text"):
                value = task.get(key)
                if value:
                    return str(value)
        if task is not None:
            return str(task)
        for key in ("query", "user_input", "task"):
            value = kwargs.get(key)
            if value:
                return str(value)
        if context_bus is not None:
            shared = context_bus.get("user_input") if hasattr(context_bus, "get") else None
            if shared:
                return str(shared)
        return ""


    def execute(self, context_bus, task: Any | None = None, **kwargs):
        query = self._task_text(task, context_bus, kwargs)
        limit = int(kwargs.get("limit", 5))
        snapshot = {}
        if self.knowledge_store is not None:
            try:
                documents = self.knowledge_store.list_documents()
            except Exception:
                documents = []
            try:
                chunks = self.knowledge_store.list_chunks()
            except Exception:
                chunks = []
            try:
                retrieval_results = self.knowledge_store.search(query, limit=limit) if query else []
            except Exception:
                retrieval_results = []
            snapshot = {
                "query": query,
                "documents": documents,
                "chunks": chunks,
                "retrieval_results": retrieval_results,
            }
        else:
            shared_documents = []
            shared_chunks = []
            retrieval_results = []
            if context_bus is not None:
                shared_documents = context_bus.get("knowledge_documents", []) or []
                shared_chunks = context_bus.get("knowledge_chunks", []) or []
                retrieval_results = context_bus.get("knowledge_retrieval_results", []) or []
            snapshot = {
                "query": query,
                "documents": shared_documents,
                "chunks": shared_chunks,
                "retrieval_results": retrieval_results,
            }

        summary_parts = [
            f"Dokumente: {len(snapshot.get('documents', []))}",
            f"Chunks: {len(snapshot.get('chunks', []))}",
            f"Treffer: {len(snapshot.get('retrieval_results', []))}",
        ]
        snapshot["summary"] = "; ".join(summary_parts)
        snapshot["sources_used"] = [item.get("source", item.get("url")) for item in snapshot.get("retrieval_results", []) if isinstance(item, dict)]

        if context_bus is not None:
            context_bus.set("knowledge", snapshot)
            context_bus.publish("knowledge", snapshot, source=self.name)
            context_bus.add_agent_report(self.name, snapshot)
        return snapshot
