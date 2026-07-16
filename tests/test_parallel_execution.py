import time
import unittest

from helpers import install_dummy_ollama


install_dummy_ollama()

from agent_registry import AgentRegistry
from agents.base_agent import BaseAgent
from agent_router import AgentRouter
from context_bus import ContextBus
from orchestrator import Orchestrator


class SlowAgent(BaseAgent):

    def __init__(self, name, delay):
        super().__init__(
            name=name,
            role="test",
            description="Slow agent",
            capabilities=["parallel"],
            allowed_tools=[],
            priority=1,
        )
        self.delay = delay


    def execute(self, context_bus, task=None, **kwargs):
        time.sleep(self.delay)
        context_bus.add_agent_report(self.name, {"task": task, "delay": self.delay})
        return {"agent": self.name, "delay": self.delay}


class ParallelExecutionTests(unittest.TestCase):

    def test_parallel_group_executes_concurrently(self):
        registry = AgentRegistry()
        registry.register(SlowAgent("slow_a", 0.2))
        registry.register(SlowAgent("slow_b", 0.2))
        router = AgentRouter(registry)
        bus = ContextBus()
        orchestrator = Orchestrator(router=router, context_bus=bus)
        orchestrator.registry.register(SlowAgent("slow_a", 0.2))
        orchestrator.registry.register(SlowAgent("slow_b", 0.2))

        start = time.perf_counter()
        outcomes = orchestrator._execute_parallel_group(["slow_a", "slow_b"], task="parallel", timeout=1.0)
        duration = time.perf_counter() - start

        self.assertEqual(len(outcomes), 2)
        self.assertLess(duration, 0.35)
        self.assertEqual(bus.get_agent_reports("slow_a")[0]["task"], "parallel")
        self.assertEqual(bus.get_agent_reports("slow_b")[0]["task"], "parallel")


if __name__ == "__main__":
    unittest.main()
