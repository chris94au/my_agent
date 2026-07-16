from __future__ import annotations


class DummySignal:

    def __init__(self):
        self._callbacks = []


    def connect(self, callback):
        self._callbacks.append(callback)


    def emit(self, *args, **kwargs):
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class FakeGUIAPI:

    def __init__(self):
        self.chat_message_added = DummySignal()
        self.stream_chunk = DummySignal()
        self.planner_updated = DummySignal()
        self.tool_events_updated = DummySignal()
        self.memory_updated = DummySignal()
        self.research_updated = DummySignal()
        self.knowledge_updated = DummySignal()
        self.tasks_updated = DummySignal()
        self.logs_updated = DummySignal()
        self.agent_dashboard_updated = DummySignal()
        self.agent_activity_updated = DummySignal()
        self.agent_communication_updated = DummySignal()
        self.context_updated = DummySignal()
        self.state_changed = DummySignal()
        self.error_occurred = DummySignal()
        self._chat_history = []
        self._planner = {
            "goal": "Projekt analysieren",
            "status": "running",
            "current_step": {"description": "Schritt 3", "action": "research"},
            "steps": [
                {"index": 1, "description": "Schritt 1", "action": "read", "status": "ok"},
                {"index": 2, "description": "Schritt 2", "action": "analyze", "status": "ok"},
                {"index": 3, "description": "Schritt 3", "action": "research", "status": "pending"},
            ],
            "errors": [],
            "reflection": {"summary": "Alles gut", "risks": [], "improvements": []},
        }
        self._memory = {
            "facts": [
                {
                    "id": 1,
                    "category": "preferences",
                    "key": "favorite_food",
                    "value": "Pasta",
                    "importance": 8,
                    "confidence": 0.9,
                    "timestamp": "2026-07-16T10:00:00+00:00",
                    "last_used_at": "2026-07-16T11:00:00+00:00",
                    "embedding": "[1,2,3]",
                }
            ],
            "summaries": [
                {
                    "id": 2,
                    "topic": "Urlaub",
                    "summary": "Benutzer plant Italien-Trip.",
                    "importance": 6,
                    "confidence": 0.8,
                    "timestamp": "2026-07-16T10:00:00+00:00",
                    "last_used_at": "2026-07-16T11:00:00+00:00",
                    "embedding": "[1,2,3]",
                }
            ],
            "relevant": "Bekannte Informationen über den Benutzer: …",
        }
        self._research = {
            "query": "beste restaurants hamburg",
            "summary": "Restaurant A ist gut.",
            "sources_used": ["https://example.com"],
            "citations": [{"claim": "Restaurant A", "source": "https://example.com", "confidence": 0.9}],
            "confidence": 0.9,
            "research_context": "Research Summary:\nRestaurant A ist gut.",
            "memory_actions": [],
        }
        self._knowledge = {
            "documents": [
                {"id": 1, "title": "Guide", "source": "file.txt", "chunk_count": 2, "import_status": "imported", "embedding": "[1,2]"}
            ],
            "retrieval_results": [
                {"chunk_index": 0, "document_id": 1, "score": 0.92, "content": "Chunk text"}
            ],
            "memory_summaries": self._memory["summaries"],
            "memory_facts": self._memory["facts"],
        }
        self._tasks = [
            {"id": 1, "title": "Analyse Report", "status": "active", "progress": 0.4, "priority": 4, "next_step": "Read doc", "scheduled_for": None}
        ]
        self._agents = [
            {"name": "planner_agent", "role": "planner", "description": "Planung", "version": "1.0", "capabilities": ["planning"], "allowed_tools": [], "denied_tools": [], "priority": 100},
            {"name": "research_agent", "role": "research", "description": "Recherche", "version": "1.0", "capabilities": ["research"], "allowed_tools": ["web_search"], "denied_tools": ["filesystem:write"], "priority": 80},
            {"name": "critic_agent", "role": "critic", "description": "Review", "version": "1.0", "capabilities": ["critique"], "allowed_tools": [], "denied_tools": ["filesystem:write"], "priority": 90},
        ]
        self._activity = [
            {"source": "planner_agent", "payload": {"goal": "Projekt analysieren"}, "timestamp": "2026-07-16T10:00:00+00:00"},
            {"source": "research_agent", "payload": {"summary": "Research summary"}, "timestamp": "2026-07-16T10:01:00+00:00"},
        ]
        self._context = {"shared": {"user_input": ""}, "agent_reports": {}, "tool_results": [], "sources": [], "memory_context": {}, "events": []}
        self._logs = [
            {"timestamp": "2026-07-16T10:00:00+00:00", "logger_name": "planner", "level": "INFO", "message": "Planner started"}
        ]
        self._tools = [
            {"name": "web_search", "description": "Search", "parameters": []}
        ]
        self._settings = {
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
        self.sent_messages = []
        self.refresh_called = False


    def start(self):
        return self


    def send_message(self, message, stream=True):
        self.sent_messages.append(message)
        self._chat_history.append({"role": "user", "content": message, "timestamp": "now"})
        self.chat_message_added.emit({"role": "user", "content": message, "timestamp": "now"})
        self.stream_chunk.emit("Antwort")
        self._chat_history.append({"role": "assistant", "content": "Antwort", "timestamp": "now"})
        self.chat_message_added.emit({"role": "assistant", "content": "Antwort", "timestamp": "now"})
        self.planner_updated.emit(self._planner)
        self.research_updated.emit(self._research)
        self.memory_updated.emit(self._memory)
        self.knowledge_updated.emit(self._knowledge)
        self.tasks_updated.emit(self._tasks)
        self.logs_updated.emit(self._logs)
        self.agent_dashboard_updated.emit(self.get_agent_dashboard())
        self.agent_activity_updated.emit(self.get_agent_activity())
        self.agent_communication_updated.emit(self.get_agent_communication())
        self.context_updated.emit(self.get_context_snapshot())
        self.state_changed.emit()
        return None


    def send_message_sync(self, message, stream=False):
        self.send_message(message, stream=stream)
        return "Antwort"


    def new_conversation(self):
        self._chat_history = []


    def clear_conversation(self):
        self._chat_history = []


    def regenerate_last(self, stream=True):
        return self.send_message("erneut", stream=stream)


    def get_chat_history(self):
        return list(self._chat_history)


    def get_planner_snapshot(self):
        return dict(self._planner)


    def get_agent_dashboard(self):
        return {"agents": list(self._agents), "route": {"agents": [agent["name"] for agent in self._agents]}, "answer": "Antwort", "status": "ready"}


    def get_agent_activity(self):
        return list(self._activity)


    def get_agent_communication(self):
        return dict(self._context)


    def get_context_snapshot(self):
        return dict(self._context)


    def get_tool_events(self, status=None):
        events = [
            {"timestamp": "2026-07-16T10:00:00+00:00", "tool": "web_search", "input": "{}", "result": "{}", "status": "ok", "runtime_ms": 12.4, "error": None},
            {"timestamp": "2026-07-16T10:01:00+00:00", "tool": "write_file", "input": "{}", "result": "{}", "status": "error", "runtime_ms": 4.1, "error": "denied"},
        ]
        if status:
            return [event for event in events if event["status"] == status]
        return events


    def get_memory_snapshot(self, query=None):
        return dict(self._memory)


    def search_memory(self, query):
        return list(self._memory["facts"])


    def update_memory_record(self, kind, record_id, **changes):
        return True


    def delete_memory_record(self, kind, record_id):
        return True


    def get_memory_history(self, kind, record_id):
        return ["Historie 1", "Historie 2"]


    def get_research_snapshot(self):
        return dict(self._research)


    def get_knowledge_snapshot(self):
        return dict(self._knowledge)


    def import_knowledge_document(self, title, source, content):
        self._knowledge["documents"].append({"id": 2, "title": title, "source": source, "chunk_count": 1, "import_status": "imported", "embedding": "[1]"})
        return 2


    def reindex_knowledge_base(self):
        return True


    def delete_knowledge_document(self, document_id):
        return True


    def get_tasks(self):
        return list(self._tasks)


    def add_task(self, title, **kwargs):
        self._tasks.append({"id": 2, "title": title, "status": "active", "progress": 0.0, "priority": kwargs.get("priority", 3), "next_step": "", "scheduled_for": None})
        return 2


    def pause_task(self, task_id):
        return True


    def resume_task(self, task_id):
        return True


    def cancel_task(self, task_id):
        return True


    def prioritize_task(self, task_id, priority):
        return True


    def set_task_progress(self, task_id, progress, next_step=None):
        return True


    def get_logs(self, logger_name=None, level=None):
        return list(self._logs)


    def export_logs(self, path):
        return path


    def get_settings(self):
        return dict(self._settings)


    def update_settings(self, **changes):
        self._settings.update(changes)
        return dict(self._settings)


    def refresh_all(self):
        self.refresh_called = True
        self.state_changed.emit()
        self.memory_updated.emit(self._memory)
        self.planner_updated.emit(self._planner)
        self.research_updated.emit(self._research)
        self.knowledge_updated.emit(self._knowledge)
        self.tasks_updated.emit(self._tasks)
        self.logs_updated.emit(self._logs)
        self.tool_events_updated.emit(self.get_tool_events())
        self.agent_dashboard_updated.emit(self.get_agent_dashboard())
        self.agent_activity_updated.emit(self.get_agent_activity())
        self.agent_communication_updated.emit(self.get_agent_communication())
        self.context_updated.emit(self.get_context_snapshot())
        return True
