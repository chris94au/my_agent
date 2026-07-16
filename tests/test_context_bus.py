import unittest

from context_bus import ContextBus


class ContextBusTests(unittest.TestCase):

    def test_bus_stores_state_and_notifies_subscribers(self):
        bus = ContextBus()
        seen = []
        bus.subscribe("plan", lambda event: seen.append((event.kind, event.source)))

        bus.set("answer", "Hallo")
        bus.set_memory_context({"query": "Hallo", "relevant": "Nichts"})
        bus.add_agent_report("planner_agent", {"goal": "Hallo"})
        bus.add_tool_result("web_search", {"results": 1}, agent_name="research_agent")
        bus.add_source({"url": "https://example.com"})
        bus.publish("plan", {"goal": "Hallo"}, source="planner_agent")

        snapshot = bus.snapshot()
        self.assertEqual(snapshot["shared"]["answer"], "Hallo")
        self.assertEqual(snapshot["memory_context"]["query"], "Hallo")
        self.assertEqual(snapshot["agent_reports"]["planner_agent"][0]["goal"], "Hallo")
        self.assertEqual(snapshot["tool_results"][0]["tool"], "web_search")
        self.assertEqual(snapshot["sources"][0]["url"], "https://example.com")
        self.assertEqual(seen[0], ("plan", "planner_agent"))
        self.assertIn("Shared Context:", bus.compose_context())


if __name__ == "__main__":
    unittest.main()
