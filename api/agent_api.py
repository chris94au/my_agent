from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PySide6.QtCore import QObject, Signal

from agent import Agent
from embedding import Embedding
from memory import Memory
from normalizer import Normalizer
from similarity import cosine_similarity
from research.pipeline import ResearchResult


logger = logging.getLogger(__name__)


ROOT = Path(__file__).resolve().parent.parent
GUI_STATE_DIR = ROOT / "workspace" / "gui"
GUI_STATE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str


@dataclass
class ToolEvent:
    timestamp: str
    agent: str
    tool: str
    input: str
    result: str
    status: str
    error: str | None = None


@dataclass
class TaskRecord:
    id: int
    title: str
    status: str = "active"
    progress: float = 0.0
    priority: int = 3
    next_step: str = ""
    scheduled_for: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class KnowledgeDocument:
    id: int
    title: str
    source: str
    content: str
    chunk_count: int
    import_status: str
    created_at: str
    embedding_present: bool


@dataclass
class LogEntry:
    timestamp: str
    logger_name: str
    level: str
    message: str


class LogBuffer:

    def __init__(self, limit: int = 1000):
        self.limit = limit
        self._records: list[LogEntry] = []
        self._lock = threading.RLock()


    def add(self, logger_name: str, level: str, message: str):
        with self._lock:
            self._records.append(
                LogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    logger_name=logger_name,
                    level=level,
                    message=message,
                )
            )
            if len(self._records) > self.limit:
                self._records = self._records[-self.limit :]


    def all(self):
        with self._lock:
            return [asdict(item) for item in self._records]


    def filtered(self, logger_name: str | None = None, level: str | None = None):
        entries = self.all()
        if logger_name:
            entries = [entry for entry in entries if logger_name.lower() in entry["logger_name"].lower()]
        if level:
            entries = [entry for entry in entries if entry["level"] == level]
        return entries


    def export(self, target_path: str | Path):
        target = Path(target_path)
        target.write_text(json.dumps(self.all(), ensure_ascii=False, indent=2), encoding="utf-8")
        return target


class QtLogHandler(logging.Handler):

    def __init__(self, buffer: LogBuffer):
        super().__init__()
        self.buffer = buffer


    def emit(self, record):
        try:
            self.buffer.add(
                logger_name=record.name,
                level=record.levelname,
                message=self.format(record),
            )
        except Exception:
            pass


class SettingsStore:

    DEFAULTS = {
        "llm_model": "qwen2.5:7b",
        "embedding_model": "nomic-embed-text",
        "temperature": 0.7,
        "context_size": 8192,
        "memory_enabled": True,
        "research_enabled": True,
        "knowledge_base_enabled": True,
        "scheduler_enabled": True,
        "theme": "System",
        "logging_enabled": True,
        "auto_save_interval": 10,
    }

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or GUI_STATE_DIR / "settings.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()


    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    merged = dict(self.DEFAULTS)
                    merged.update(data)
                    return merged
            except Exception:
                logger.warning("Failed to load settings file, using defaults")
        return dict(self.DEFAULTS)


    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.data


    def get(self, key, default=None):
        return self.data.get(key, default)


    def update(self, **changes):
        self.data.update(changes)
        return self.save()


    def snapshot(self):
        return dict(self.data)


class TaskStore:

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or GUI_STATE_DIR / "tasks.db")
        self.connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._ensure_schema()
        self._lock = threading.RLock()


    def _ensure_schema(self):
        cur = self.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                progress REAL NOT NULL DEFAULT 0.0,
                priority INTEGER NOT NULL DEFAULT 3,
                next_step TEXT NOT NULL DEFAULT '',
                scheduled_for TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()


    def add(self, title, status="active", progress=0.0, priority=3, next_step="", scheduled_for=None):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute(
                """
                INSERT INTO tasks (title, status, progress, priority, next_step, scheduled_for, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (title, status, float(progress), int(priority), next_step, scheduled_for),
            )
            self.connection.commit()
            return cur.lastrowid


    def update(self, task_id, **changes):
        if not changes:
            return
        allowed = {"title", "status", "progress", "priority", "next_step", "scheduled_for"}
        assignments = []
        values = []
        for key, value in changes.items():
            if key in allowed:
                assignments.append(f"{key} = ?")
                values.append(value)
        if not assignments:
            return
        values.extend([task_id])
        with self._lock:
            self.connection.execute(
                f"UPDATE tasks SET {', '.join(assignments)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values,
            )
            self.connection.commit()


    def list(self, status: str | None = None):
        query = "SELECT * FROM tasks"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY priority DESC, updated_at DESC, id DESC"
        rows = self.connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]


    def set_status(self, task_id, status):
        self.update(task_id, status=status)


    def pause(self, task_id):
        self.set_status(task_id, "paused")


    def resume(self, task_id):
        self.set_status(task_id, "active")


    def cancel(self, task_id):
        self.set_status(task_id, "canceled")


    def prioritize(self, task_id, priority):
        self.update(task_id, priority=priority)


class KnowledgeStore:

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or GUI_STATE_DIR / "knowledge.db")
        self.connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.embedding = Embedding()
        self._ensure_schema()
        self._lock = threading.RLock()


    def _ensure_schema(self):
        cur = self.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                import_status TEXT NOT NULL DEFAULT 'imported',
                embedding TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        self.connection.commit()


    def _chunk_content(self, content: str, chunk_size: int = 800):
        text = " ".join(str(content).split())
        if not text:
            return []
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


    def import_document(self, title: str, source: str, content: str):
        chunks = self._chunk_content(content)
        with self._lock:
            cur = self.connection.cursor()
            embedding = self.embedding.create(f"{title}\n{content[:2000]}") if content else None
            cur.execute(
                """
                INSERT INTO documents (title, source, content, chunk_count, import_status, embedding, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'imported', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (title, source, content, len(chunks), json.dumps(embedding) if embedding else None),
            )
            document_id = cur.lastrowid
            for index, chunk in enumerate(chunks):
                chunk_embedding = self.embedding.create(chunk)
                cur.execute(
                    """
                    INSERT INTO chunks (document_id, chunk_index, content, embedding, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (document_id, index, chunk, json.dumps(chunk_embedding)),
                )
            self.connection.commit()
            return document_id


    def delete_document(self, document_id: int):
        with self._lock:
            self.connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            self.connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            self.connection.commit()


    def reindex(self):
        with self._lock:
            docs = self.connection.execute("SELECT * FROM documents").fetchall()
            for doc in docs:
                content = doc["content"]
                embedding = self.embedding.create(f"{doc['title']}\n{content[:2000]}") if content else None
                self.connection.execute(
                    "UPDATE documents SET embedding = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (json.dumps(embedding) if embedding else None, doc["id"]),
                )
                chunks = self.connection.execute("SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index", (doc["id"],)).fetchall()
                for chunk in chunks:
                    chunk_embedding = self.embedding.create(chunk["content"])
                    self.connection.execute(
                        "UPDATE chunks SET embedding = ? WHERE id = ?",
                        (json.dumps(chunk_embedding), chunk["id"]),
                    )
            self.connection.commit()


    def list_documents(self):
        rows = self.connection.execute("SELECT * FROM documents ORDER BY updated_at DESC, id DESC").fetchall()
        return [dict(row) for row in rows]


    def list_chunks(self, document_id: int | None = None):
        query = "SELECT * FROM chunks"
        params = []
        if document_id is not None:
            query += " WHERE document_id = ?"
            params.append(document_id)
        query += " ORDER BY document_id DESC, chunk_index ASC"
        rows = self.connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]


    def search(self, query: str, limit: int = 10):
        query_embedding = self.embedding.create(query)
        results = []
        for row in self.connection.execute("SELECT * FROM chunks").fetchall():
            if not row["embedding"]:
                continue
            try:
                embedding = json.loads(row["embedding"])
            except Exception:
                continue
            score = cosine_similarity(query_embedding, embedding)
            results.append(
                {
                    **dict(row),
                    "score": score,
                }
            )
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]


class AgentAPI(QObject):

    state_changed = Signal()
    chat_message_added = Signal(dict)
    stream_chunk = Signal(str)
    planner_updated = Signal(dict)
    tool_events_updated = Signal(list)
    memory_updated = Signal(dict)
    research_updated = Signal(dict)
    knowledge_updated = Signal(dict)
    tasks_updated = Signal(list)
    logs_updated = Signal(list)
    error_occurred = Signal(str)


    def __init__(self, model: str = "qwen2.5:7b", settings_path: str | Path | None = None):
        super().__init__()
        self.model = model
        self.settings_store = SettingsStore(settings_path)
        self.task_store = TaskStore()
        self.knowledge_store = KnowledgeStore()
        self.log_buffer = LogBuffer()
        self._log_handler = QtLogHandler(self.log_buffer)
        self._log_handler.setFormatter(logging.Formatter("%(name)s | %(levelname)s | %(message)s"))
        self._install_logging()
        self._agent: Agent | None = None
        self._lock = threading.RLock()
        self._chat_history: list[ChatMessage] = []
        self._last_user_message: str | None = None
        self._last_answer: str | None = None
        self._last_send_thread: threading.Thread | None = None
        self._last_state: dict[str, Any] = {}
        self._research_history: list[dict] = []


    def _install_logging(self):
        root_logger = logging.getLogger()
        if self._log_handler not in root_logger.handlers:
            root_logger.addHandler(self._log_handler)
        if root_logger.level > logging.INFO:
            root_logger.setLevel(logging.INFO)


    def start(self):
        with self._lock:
            if self._agent is None:
                self._agent = Agent(model=self.settings_store.get("llm_model", self.model))
            return self._agent


    @property
    def agent(self):
        return self.start()


    def _now(self):
        return datetime.now(timezone.utc).isoformat()


    def _append_chat(self, role: str, content: str):
        entry = ChatMessage(role=role, content=content, timestamp=self._now())
        self._chat_history.append(entry)
        self.chat_message_added.emit(asdict(entry))
        return entry


    def _emit_state(self):
        self.state_changed.emit()
        self.memory_updated.emit(self.get_memory_snapshot())
        self.planner_updated.emit(self.get_planner_snapshot())
        self.research_updated.emit(self.get_research_snapshot())
        self.tool_events_updated.emit(self.get_tool_events())
        self.knowledge_updated.emit(self.get_knowledge_snapshot())
        self.tasks_updated.emit(self.get_tasks())
        self.logs_updated.emit(self.get_logs())


    def _process_answer(self, message: str, stream: bool = True):
        try:
            answer = self.agent.think(message)
            if stream:
                chunks = self._chunk_text(answer)
                for chunk in chunks:
                    self.stream_chunk.emit(chunk)
                    time.sleep(0.015)
            with self._lock:
                self._last_answer = answer
                self._last_state = self._build_state_snapshot()
                self._append_chat("assistant", answer)
                research_result = self._last_state.get("research", {})
                if research_result:
                    self._research_history.append(research_result)
                    if len(self._research_history) > 20:
                        self._research_history = self._research_history[-20:]
                    if self._last_state.get("research", {}).get("memory_actions"):
                        self._emit_state()
            self._emit_state()
        except Exception as exc:
            logger.exception("Agent API failed")
            self.error_occurred.emit(str(exc))


    def _chunk_text(self, text: str, chunk_size: int = 24):
        text = str(text)
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or [""]


    def send_message(self, message: str, stream: bool = True):
        self.start()
        self._last_user_message = message
        self._append_chat("user", message)
        worker = threading.Thread(target=self._process_answer, args=(message, stream), daemon=True)
        self._last_send_thread = worker
        worker.start()
        return worker


    def send_message_sync(self, message: str, stream: bool = False):
        self.start()
        self._last_user_message = message
        self._append_chat("user", message)
        answer = self.agent.think(message)
        self._last_answer = answer
        self._last_state = self._build_state_snapshot()
        self._append_chat("assistant", answer)
        self._emit_state()
        return answer


    def regenerate_last(self, stream: bool = True):
        if not self._last_user_message:
            return None
        return self.send_message(self._last_user_message, stream=stream)


    def clear_conversation(self):
        self._chat_history = []
        self._last_user_message = None
        self._last_answer = None
        self._last_state = {}
        if self._agent is not None:
            self._agent.conversation = self._agent.conversation.__class__(self._agent.system_prompt)
            self._agent.last_plan = None
            self._agent.last_execution = None
            self._agent.last_reflection = None
            self._agent.last_research_result = None
            self._agent.last_answer = None
        self._emit_state()


    def new_conversation(self):
        self.clear_conversation()


    def get_chat_history(self):
        return [asdict(item) for item in self._chat_history]


    def _build_state_snapshot(self):
        planner = self.get_planner_snapshot()
        research = self.get_research_snapshot()
        memory = self.get_memory_snapshot()
        tools = self.get_tool_events()
        tasks = self.get_tasks()
        knowledge = self.get_knowledge_snapshot()
        logs = self.get_logs()
        return {
            "planner": planner,
            "research": research,
            "memory": memory,
            "tools": tools,
            "tasks": tasks,
            "knowledge": knowledge,
            "logs": logs,
        }


    def get_memory_snapshot(self, query: str | None = None):
        agent = self.start()
        facts = agent.memory.get_all_facts()
        summaries = agent.memory.get_all_summaries()
        relevant = agent.memory.get_semantic_context(query or self._last_user_message or "") if query or self._last_user_message else agent.memory.get_context()
        snapshot = {
            "facts": facts,
            "summaries": summaries,
            "relevant": relevant,
            "query": query or self._last_user_message or "",
        }
        return snapshot


    def get_memory(self):
        return self.get_memory_snapshot()


    def _memory_table_name(self, kind: str):
        return "facts" if str(kind).lower() in {"fact", "facts"} else "summaries"


    def update_memory_record(self, kind: str, record_id: int, **changes):
        table = self._memory_table_name(kind)
        allowed = {"category", "key", "value", "topic", "summary", "importance", "confidence", "status"}
        assignments = []
        values = []
        for key, value in changes.items():
            if key in allowed:
                assignments.append(f"{key} = ?")
                values.append(value)
        if not assignments:
            return False
        assignments.append("last_seen_at = CURRENT_TIMESTAMP")
        assignments.append("last_used_at = CURRENT_TIMESTAMP")
        values.append(record_id)
        query = f"UPDATE {table} SET {', '.join(assignments)} WHERE id = ?"
        if hasattr(self.start().memory, "connection"):
            conn = self.start().memory.connection
            conn.execute(query, values)
            conn.commit()
            self.memory_updated.emit(self.get_memory_snapshot())
            return True
        return False


    def delete_memory_record(self, kind: str, record_id: int):
        table = self._memory_table_name(kind)
        if hasattr(self.start().memory, "connection"):
            conn = self.start().memory.connection
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
            conn.commit()
            self.memory_updated.emit(self.get_memory_snapshot())
            return True
        return False


    def get_memory_history(self, kind: str, record_id: int):
        table = self._memory_table_name(kind)
        if not hasattr(self.start().memory, "connection"):
            return []
        conn = self.start().memory.connection
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone()
        if not row:
            return []
        row = dict(row)
        history = [
            f"Erstellt: {row.get('timestamp', '')}",
            f"Zuletzt gesehen: {row.get('last_seen_at', '')}",
            f"Zuletzt verwendet: {row.get('last_used_at', '')}",
            f"Status: {row.get('status', '')}",
        ]
        if row.get("archive_reason"):
            history.append(f"Archivgrund: {row.get('archive_reason')}")
        return history


    def search_memory(self, query: str):
        agent = self.start()
        return agent.memory.search(query)


    def get_planner_snapshot(self):
        agent = self.start()
        plan = getattr(agent, "last_plan", None)
        execution = getattr(agent, "last_execution", None) or {}
        reflection = getattr(agent, "last_reflection", None)
        if plan is None:
            return {
                "goal": "",
                "steps": [],
                "current_step": None,
                "status": "idle",
                "errors": [],
                "reflection": None,
            }

        steps = []
        step_results = execution.get("step_results", []) if isinstance(execution, dict) else []
        for index, step in enumerate(plan.steps, start=1):
            result = step_results[index - 1] if index - 1 < len(step_results) else {}
            steps.append(
                {
                    "index": index,
                    "action": step.action,
                    "description": step.description,
                    "status": result.get("status", "pending" if index > len(step_results) else "ok"),
                    "result": result.get("result"),
                }
            )

        current_step = next((step for step in steps if step["status"] in {"pending", "error"}), None)
        if current_step is None and steps:
            current_step = steps[-1]
        return {
            "goal": plan.goal,
            "steps": steps,
            "current_step": current_step,
            "status": "complete" if execution else "planned",
            "errors": getattr(plan, "validation_errors", []),
            "reflection": asdict(reflection) if reflection and hasattr(reflection, "__dict__") else reflection,
        }


    def get_planner(self):
        return self.get_planner_snapshot()


    def get_research_snapshot(self):
        agent = self.start()
        research = getattr(agent, "last_research_result", None)
        if research is None and self._research_history:
            research = self._research_history[-1]
        if research is None:
            return {
                "query": "",
                "summary": "",
                "sources_used": [],
                "citations": [],
                "confidence": 0.0,
                "research_context": "",
                "memory_actions": [],
            }
        if hasattr(research, "__dict__"):
            research = research.__dict__.copy()
        return research


    def get_research(self):
        return self.get_research_snapshot()


    def get_tool_events(self, status: str | None = None):
        path = ROOT / "tool_events.db"
        if not path.exists():
            return []
        try:
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM tool_events"
            params: list[Any] = []
            if status:
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY timestamp DESC, id DESC LIMIT 200"
            rows = conn.execute(query, params).fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.warning("Failed to load tool events: %s", exc)
            return []


    def get_tools(self):
        from tools import tool_manager

        tools = []
        for tool in tool_manager.list_tools():
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": [
                        {
                            "name": parameter.name,
                            "type": parameter.type,
                            "required": parameter.required,
                            "description": parameter.description,
                        }
                        for parameter in getattr(tool, "parameters", [])
                    ],
                }
            )
        return tools


    def get_knowledge_snapshot(self):
        documents = self.knowledge_store.list_documents()
        chunks = self.knowledge_store.list_chunks()
        memory = self.get_memory_snapshot()
        return {
            "documents": documents,
            "chunks": chunks,
            "memory_summaries": memory.get("summaries", []),
            "memory_facts": memory.get("facts", []),
            "retrieval_results": self.knowledge_store.search(self._last_user_message or memory.get("query", ""), limit=10) if (self._last_user_message or memory.get("query")) else [],
        }


    def get_knowledge(self):
        return self.get_knowledge_snapshot()


    def import_knowledge_document(self, title: str, source: str, content: str):
        doc_id = self.knowledge_store.import_document(title=title, source=source, content=content)
        self.knowledge_updated.emit(self.get_knowledge_snapshot())
        return doc_id


    def reindex_knowledge_base(self):
        self.knowledge_store.reindex()
        self.knowledge_updated.emit(self.get_knowledge_snapshot())


    def delete_knowledge_document(self, document_id: int):
        self.knowledge_store.delete_document(document_id)
        self.knowledge_updated.emit(self.get_knowledge_snapshot())


    def get_tasks(self):
        return self.task_store.list()


    def add_task(self, title: str, **kwargs):
        task_id = self.task_store.add(title, **kwargs)
        self.tasks_updated.emit(self.get_tasks())
        return task_id


    def pause_task(self, task_id: int):
        self.task_store.pause(task_id)
        self.tasks_updated.emit(self.get_tasks())


    def resume_task(self, task_id: int):
        self.task_store.resume(task_id)
        self.tasks_updated.emit(self.get_tasks())


    def cancel_task(self, task_id: int):
        self.task_store.cancel(task_id)
        self.tasks_updated.emit(self.get_tasks())


    def prioritize_task(self, task_id: int, priority: int):
        self.task_store.prioritize(task_id, priority)
        self.tasks_updated.emit(self.get_tasks())


    def set_task_progress(self, task_id: int, progress: float, next_step: str | None = None):
        changes = {"progress": progress}
        if next_step is not None:
            changes["next_step"] = next_step
        self.task_store.update(task_id, **changes)
        self.tasks_updated.emit(self.get_tasks())


    def get_logs(self, logger_name: str | None = None, level: str | None = None):
        return self.log_buffer.filtered(logger_name=logger_name, level=level)


    def export_logs(self, target_path: str | Path):
        return self.log_buffer.export(target_path)


    def get_settings(self):
        return self.settings_store.snapshot()


    def update_settings(self, **changes):
        settings = self.settings_store.update(**changes)
        self.settings_updated.emit(settings)
        return settings


    def refresh_all(self):
        self._emit_state()
        return self._last_state
