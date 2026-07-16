import unittest

from helpers import install_dummy_ollama


install_dummy_ollama()

import agent as agent_module


class FakeMemory:

    def __init__(self):
        self.fact_calls = []
        self.summary_calls = []


    def save_fact(self, **kwargs):
        self.fact_calls.append(kwargs)
        return {"status": "inserted"}


    def save_summary(self, *args, **kwargs):
        self.summary_calls.append((args, kwargs))
        return {"status": "inserted"}


    def get_semantic_context(self, query):
        return ""


class FakeExtractor:

    def extract(self, conversation):
        return [
            {
                "category": "interest",
                "key": "favorite_band",
                "value": "Metallica",
                "importance": 7
            }
        ]


class FakeValidator:

    def validate(self, memory, conversation=None):
        return {
            "approved": True,
            "importance": 8,
            "confidence": 0.93
        }


class FakeSummarizer:

    def summarize(self, conversation, memories=None):
        return {
            "topic": "Gitarrenmusik",
            "summary": "Der Benutzer spielt Gitarre und mag Metallica.",
            "importance": 6,
            "confidence": 0.8
        }


class FakePlanner:

    def __init__(self, model=None):
        self.model = model


    def plan(self, user_input, memory_context="", tool_descriptions="", available_tools=None):
        from planner import Plan, PlanStep

        return Plan(
            goal="Antwort erzeugen",
            steps=[
                PlanStep(action="respond", description="Antwort formulieren")
            ],
            raw={"goal": "Antwort erzeugen", "steps": [{"action": "respond"}]},
            valid=True,
            validation_errors=[]
        )


class FakeExecutionLoop:

    def __init__(self, model, tool_executor, tool_manager):
        self.model = model
        self.tool_executor = tool_executor
        self.tool_manager = tool_manager
        self.calls = []


    def run(self, user_input, memory_context, plan):
        self.calls.append((user_input, memory_context, plan.goal))
        return {
            "answer": "Fertig.",
            "step_results": [
                {
                    "action": "respond",
                    "input": None,
                    "result": "Fertig.",
                    "status": "ok"
                }
            ],
            "plan": plan
        }


class AgentPipelineTests(unittest.TestCase):

    def setUp(self):
        self._original_memory = agent_module.Memory
        self._original_extractor = agent_module.MemoryExtractor
        self._original_validator = agent_module.MemoryValidator
        self._original_summarizer = agent_module.ConversationSummarizer
        self._original_planner = agent_module.Planner
        self._original_execution_loop = agent_module.ExecutionLoop

        agent_module.Memory = FakeMemory
        agent_module.MemoryExtractor = FakeExtractor
        agent_module.MemoryValidator = FakeValidator
        agent_module.ConversationSummarizer = FakeSummarizer
        agent_module.Planner = FakePlanner
        agent_module.ExecutionLoop = FakeExecutionLoop

        self.agent = agent_module.Agent()


    def tearDown(self):
        agent_module.Memory = self._original_memory
        agent_module.MemoryExtractor = self._original_extractor
        agent_module.MemoryValidator = self._original_validator
        agent_module.ConversationSummarizer = self._original_summarizer
        agent_module.Planner = self._original_planner
        agent_module.ExecutionLoop = self._original_execution_loop


    def test_update_memory_uses_pipeline_and_normalizes_values(self):
        self.agent.update_memory(
            "User: Ich höre gern Metallica und spiele Gitarre."
        )

        self.assertEqual(len(self.agent.memory.fact_calls), 1)
        fact_call = self.agent.memory.fact_calls[0]
        self.assertEqual(fact_call["category"], "Interessen")
        self.assertEqual(fact_call["key"], "Lieblingsband")
        self.assertEqual(fact_call["value"], "Metallica")
        self.assertEqual(fact_call["importance"], 8)
        self.assertAlmostEqual(fact_call["confidence"], 0.93, places=2)

        self.assertEqual(len(self.agent.memory.summary_calls), 1)
        summary_args, summary_kwargs = self.agent.memory.summary_calls[0]
        self.assertEqual(summary_args[0], "Gitarrenmusik")
        self.assertEqual(summary_args[1], "Der Benutzer spielt Gitarre und mag Metallica.")
        self.assertEqual(summary_kwargs["importance"], 6)
        self.assertAlmostEqual(summary_kwargs["confidence"], 0.8, places=2)


    def test_think_uses_planner_and_execution_loop(self):
        answer = self.agent.think("Analysiere die Datei example.txt")
        self.assertEqual(answer, "Fertig.")
        self.assertIn("Fertig.", self.agent.conversation.get_messages()[-1]["content"])


if __name__ == "__main__":
    unittest.main()
