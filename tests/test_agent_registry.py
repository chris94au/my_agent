import unittest

from agents.base_agent import BaseAgent
from agents.agent_factory import AgentFactory
from agents.agent_manager import AgentManager
from agent_registry import AgentRegistry
from context_bus import ContextBus


class DummyAgent(BaseAgent):

    def __init__(self, name="dummy_agent", role="test", description="Dummy agent", **kwargs):
        super().__init__(
            name=name,
            role=role,
            description=description,
            capabilities=["testing", "routing"],
            allowed_tools=["safe_tool"],
            priority=kwargs.pop("priority", 10),
        )
        self.calls = []


    def execute(self, context_bus, task=None, **kwargs):
        self.calls.append((task, kwargs))
        context_bus.set("dummy", task)
        return {"task": task, "kwargs": kwargs}


class AgentRegistryTests(unittest.TestCase):

    def test_registry_registers_and_filters_agents(self):
        registry = AgentRegistry()
        agent = DummyAgent()
        registry.register(agent)

        self.assertIs(registry.get("dummy_agent"), agent)
        self.assertIn("dummy_agent", registry)
        self.assertEqual(registry.versions()["dummy_agent"], "1.0")
        self.assertEqual(registry.priorities()["dummy_agent"], 10)
        self.assertEqual(registry.allowed_tools()["dummy_agent"], ["safe_tool"])
        self.assertEqual(registry.find_by_capability("routing")[0], agent)
        self.assertEqual(registry.find_by_tool("safe_tool")[0], agent)


    def test_manager_and_factory_execute_registered_agents(self):
        registry = AgentRegistry()
        factory = AgentFactory(registry)
        manager = AgentManager(registry)
        agent = factory.create(DummyAgent)
        bus = ContextBus()

        outcome = manager.execute(agent.name, bus, task="hello", extra=True)
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.output["task"], "hello")
        self.assertEqual(bus.get("dummy"), "hello")
        self.assertEqual(agent.calls[0][1]["extra"], True)


if __name__ == "__main__":
    unittest.main()
