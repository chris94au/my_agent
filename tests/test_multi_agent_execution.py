import unittest

from helpers import install_dummy_ollama


install_dummy_ollama()

import orchestrator as orchestrator_module
from orchestrator import Orchestrator


class FakeResearchPipeline:

    def __init__(self, model=None, memory=None):
        self.model = model
        self.memory = memory


    def run(self, query, memory_context="", limit=5):
        return type(
            "ResearchResult",
            (),
            {
                "query": query,
                "summary": "Fake research summary",
                "sources_used": ["https://example.com"],
                "citations": [],
                "confidence": 0.9,
                "research_context": "Research Summary:\nFake research summary",
                "memory_actions": [],
            },
        )()


class MultiAgentExecutionTests(unittest.TestCase):

    def setUp(self):
        self._original_research_pipeline = orchestrator_module.ResearchPipeline
        orchestrator_module.ResearchPipeline = FakeResearchPipeline


    def tearDown(self):
        orchestrator_module.ResearchPipeline = self._original_research_pipeline


    def test_research_and_knowledge_agents_can_run_via_router(self):
        orchestrator = Orchestrator()
        result = orchestrator.think("Vergleiche aktuelle Quellen zu Python-Frameworks.")
        context = result.context
        self.assertIn("research", context.get("shared", {}))
        self.assertIn("knowledge", context.get("shared", {}))
        self.assertTrue(result.outcomes)


if __name__ == "__main__":
    unittest.main()
