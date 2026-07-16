import unittest

from helpers import install_dummy_ollama


install_dummy_ollama()

from orchestrator import Orchestrator


class OrchestratorTests(unittest.TestCase):

    def test_orchestrator_runs_and_exposes_snapshot(self):
        orchestrator = Orchestrator()
        result = orchestrator.think("Sag hallo")

        self.assertEqual(result.task, "Sag hallo")
        self.assertIsNotNone(result.plan)
        self.assertTrue(result.final_response)
        snapshot = orchestrator.snapshot()
        self.assertEqual(snapshot["answer"], result.final_response)
        self.assertIn("plan", snapshot)
        self.assertIn("context", snapshot)


if __name__ == "__main__":
    unittest.main()
