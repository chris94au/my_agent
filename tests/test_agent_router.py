import unittest

from agent_registry import AgentRegistry
from agent_router import AgentRouter
from agents.base_agent import BaseAgent


class DummyAgent(BaseAgent):

    def __init__(self, name, role, description, priority=1):
        super().__init__(
            name=name,
            role=role,
            description=description,
            capabilities=[role],
            allowed_tools=[],
            priority=priority,
        )


    def execute(self, context_bus, task=None, **kwargs):
        return {"ok": True}


class AgentRouterTests(unittest.TestCase):

    def setUp(self):
        registry = AgentRegistry()
        for name, role, description, priority in [
            ("planner_agent", "planner", "Planner", 100),
            ("research_agent", "research", "Research", 80),
            ("knowledge_agent", "knowledge", "Knowledge", 60),
            ("memory_agent", "memory", "Memory", 70),
            ("coding_agent", "coding", "Coding", 75),
            ("critic_agent", "critic", "Critic", 90),
            ("vision_agent", "vision", "Vision", 65),
            ("task_agent", "task", "Task", 55),
        ]:
            registry.register(DummyAgent(name, role, description, priority=priority))
        self.router = AgentRouter(registry)


    def test_routes_code_requests_to_planner_coding_and_critic(self):
        decision = self.router.route("Schreibe mir ein Python-Programm.")
        self.assertEqual(decision.agents[0], "planner_agent")
        self.assertIn("coding_agent", decision.agents)
        self.assertEqual(decision.agents[-1], "critic_agent")


    def test_routes_image_requests_to_vision_stack(self):
        decision = self.router.route("Analysiere dieses Bild.")
        self.assertEqual(decision.agents[0], "vision_agent")
        self.assertIn("knowledge_agent", decision.agents)
        self.assertEqual(decision.agents[-1], "critic_agent")


    def test_routes_personal_preference_requests_to_memory_and_research(self):
        decision = self.router.route("Welche Gitarrenmusik passt zu mir?")
        self.assertIn("memory_agent", decision.agents)
        self.assertIn("research_agent", decision.agents)
        self.assertEqual(decision.agents[-1], "critic_agent")


if __name__ == "__main__":
    unittest.main()
