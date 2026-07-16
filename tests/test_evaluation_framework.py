import unittest

from evaluation import EvaluationFramework


class FakeResult:

    def __init__(self):
        self.task = "Recherche"
        self.plan = type("Plan", (), {"valid": True, "steps": [1, 2], "validation_errors": []})()
        self.context = {
            "route_decision": {"agents": ["planner_agent", "research_agent", "critic_agent"], "confidence": 0.8},
            "shared": {"user_input": "Recherche"},
            "agent_reports": {"planner_agent": [{"goal": "Recherche"}], "research_agent": [{"summary": "ok"}]},
            "tool_results": [{"tool": "web_search"}],
            "step_results": [{"action": "research", "status": "ok"}, {"action": "respond", "status": "ok"}],
            "events": [{"kind": "agent_outcome"}],
        }


class EvaluationFrameworkTests(unittest.TestCase):

    def test_evaluation_produces_metrics(self):
        framework = EvaluationFramework()
        result = framework.evaluate_orchestration(FakeResult(), runtime_ms=950)
        self.assertGreater(result.metrics.total, 0)
        self.assertGreater(result.metrics.plan_quality, 0)
        self.assertGreater(result.metrics.communication_quality, 0)
        self.assertGreater(result.metrics.tool_usage, 0)


if __name__ == "__main__":
    unittest.main()
