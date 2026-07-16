import unittest

from helpers import install_dummy_ollama


ollama = install_dummy_ollama()

from planner import Planner


class PlannerTests(unittest.TestCase):

    def setUp(self):
        self.planner = Planner(model="test-model")


    def test_planner_parses_structured_llm_output(self):
        original_chat = ollama.chat

        def fake_chat(model, messages):
            return {
                "message": {
                    "content": """
                    {
                        "goal": "Datei analysieren",
                        "steps": [
                            {
                                "action": "read_file",
                                "input": "example.txt",
                                "description": "Datei lesen"
                            },
                            {
                                "action": "analyze",
                                "description": "Inhalt analysieren"
                            },
                            {
                                "action": "respond",
                                "description": "Antwort formulieren"
                            }
                        ]
                    }
                    """
                }
            }

        ollama.chat = fake_chat
        try:
            plan = self.planner.plan(
                "Analysiere diese Datei und fasse die wichtigsten Punkte zusammen.",
                memory_context="Bekannte Informationen über den Benutzer:",
                tool_descriptions="read_file: Liest eine Datei",
                available_tools=["read_file"]
            )
        finally:
            ollama.chat = original_chat

        self.assertTrue(plan.valid)
        self.assertEqual(plan.goal, "Datei analysieren")
        self.assertEqual(len(plan.steps), 3)
        self.assertEqual(plan.steps[0].action, "read_file")
        self.assertEqual(plan.steps[0].input, "example.txt")
        self.assertEqual(plan.steps[-1].action, "respond")


    def test_planner_falls_back_on_invalid_output(self):
        original_chat = ollama.chat

        def fake_chat(model, messages):
            return {"message": {"content": "kein json"}}

        ollama.chat = fake_chat
        try:
            plan = self.planner.plan(
                "Sag hallo",
                memory_context="",
                tool_descriptions="",
                available_tools=[]
            )
        finally:
            ollama.chat = original_chat

        self.assertTrue(plan.valid)
        self.assertEqual(plan.steps[-1].action, "respond")


if __name__ == "__main__":
    unittest.main()
