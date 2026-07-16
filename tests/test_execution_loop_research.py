import unittest

from helpers import install_dummy_ollama


ollama = install_dummy_ollama()

from execution_loop import ExecutionLoop
from planner import Plan, PlanStep


class FakeToolExecutor:

    def execute(self, tool_name, tool_input, *, agent="agent", confirmed=False):
        return True, {"tool": tool_name, "input": tool_input}


class FakeResearchPipeline:

    def __init__(self):
        self.calls = []


    def run(self, query, memory_context="", limit=5):
        self.calls.append((query, memory_context, limit))

        class Result:
            def __init__(self):
                self.query = query
                self.summary = "Research summary"
                self.sources_used = ["https://example.com"]
                self.citations = [{"claim": "A", "source": "https://example.com", "confidence": 0.9}]
                self.confidence = 0.9
                self.research_context = "Research Summary:\nResearch summary"

        return Result()


class ExecutionLoopResearchTests(unittest.TestCase):

    def test_research_step_uses_pipeline_before_response(self):
        original_chat = ollama.chat

        def fake_chat(model, messages):
            return {"message": {"content": "Fertige Antwort"}}

        ollama.chat = fake_chat
        try:
            research_pipeline = FakeResearchPipeline()
            loop = ExecutionLoop(
                model="test-model",
                tool_executor=FakeToolExecutor(),
                tool_manager=object(),
                critic=None,
                research_pipeline=research_pipeline,
            )
            plan = Plan(
                goal="Restaurants recherchieren",
                steps=[
                    PlanStep(action="research", input="beste Restaurants Hamburg", description="Recherche durchführen"),
                    PlanStep(action="respond", description="Antwort formulieren"),
                ],
                raw={},
                valid=True,
                validation_errors=[],
            )
            result = loop.run(
                user_input="Welche Restaurants in Hamburg sind am besten bewertet?",
                memory_context="Benutzer mag italienische Küche",
                plan=plan,
            )
        finally:
            ollama.chat = original_chat

        self.assertEqual(len(research_pipeline.calls), 1)
        self.assertIn("beste Restaurants Hamburg", research_pipeline.calls[0][0])
        self.assertEqual(result["answer"], "Fertige Antwort")
        self.assertEqual(result["step_results"][0]["action"], "research")
        self.assertIn("Research summary", result["step_results"][0]["result"]["summary"])


if __name__ == "__main__":
    unittest.main()
