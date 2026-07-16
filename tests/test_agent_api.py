import unittest

from helpers import install_dummy_ollama


install_dummy_ollama()

import api.agent_api as agent_api_module


class FakeMemory:

    def __init__(self):
        self.facts = [
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
        ]
        self.summaries = []


    def get_all_facts(self):
        return list(self.facts)


    def get_all_summaries(self):
        return list(self.summaries)


    def get_semantic_context(self, query):
        return "Bekannte Informationen über den Benutzer:"


    def get_context(self):
        return "Bekannte Informationen über den Benutzer:"


class FakeAgent:

    def __init__(self, model="qwen2.5:7b"):
        self.model = model
        self.memory = FakeMemory()
        self.conversation = type("Conversation", (), {"__class__": type("Conversation", (), {})})
        self.system_prompt = "System"
        self.last_plan = None
        self.last_execution = None
        self.last_reflection = None
        self.last_research_result = None
        self.last_answer = None


    def think(self, message):
        self.last_plan = type(
            "Plan",
            (),
            {
                "goal": "Antworten",
                "steps": [type("Step", (), {"action": "respond", "description": "Antwort formulieren"})()],
                "validation_errors": [],
            },
        )()
        research_result = {
            "query": message,
            "summary": "Research summary",
            "sources_used": ["https://example.com"],
            "citations": [{"claim": "Claim", "source": "https://example.com", "confidence": 0.9}],
            "confidence": 0.88,
            "research_context": "Research Summary:\nResearch summary",
            "memory_actions": [],
        }
        self.last_execution = {
            "answer": "Fertige Antwort",
            "step_results": [
                {"action": "research", "result": research_result, "status": "ok"},
                {"action": "respond", "result": "Fertige Antwort", "status": "ok"},
            ],
        }
        self.last_research_result = research_result
        self.last_answer = "Fertige Antwort"
        return "Fertige Antwort"


class AgentAPITests(unittest.TestCase):

    def setUp(self):
        self._original_agent = agent_api_module.Agent
        agent_api_module.Agent = FakeAgent
        self.api = agent_api_module.AgentAPI()


    def tearDown(self):
        agent_api_module.Agent = self._original_agent


    def test_send_message_sync_updates_state(self):
        answer = self.api.send_message_sync("Welche Restaurants sind gut?", stream=False)
        self.assertEqual(answer, "Fertige Antwort")
        self.assertEqual(len(self.api.get_chat_history()), 2)
        planner = self.api.get_planner_snapshot()
        self.assertEqual(planner["goal"], "Antworten")
        research = self.api.get_research_snapshot()
        self.assertEqual(research["summary"], "Research summary")
        memory = self.api.get_memory_snapshot()
        self.assertTrue(memory["facts"])


    def test_task_and_knowledge_helpers_work(self):
        task_id = self.api.add_task("Analyse Report", priority=4)
        self.assertIsInstance(task_id, int)
        tasks = self.api.get_tasks()
        self.assertTrue(tasks)
        self.api.pause_task(task_id)
        self.api.resume_task(task_id)
        self.api.cancel_task(task_id)
        self.api.prioritize_task(task_id, 5)

        doc_id = self.api.import_knowledge_document("Guide", "file.txt", "Beispielinhalt")
        self.assertIsInstance(doc_id, int)
        knowledge = self.api.get_knowledge_snapshot()
        self.assertTrue(knowledge["documents"])


if __name__ == "__main__":
    unittest.main()
