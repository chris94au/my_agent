import unittest

from agents.base_agent import BaseAgent
from agents.permissions import PermissionPolicy


class DummyPermissionAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="permission_agent",
            role="test",
            description="Permission test agent",
            capabilities=["test"],
            allowed_tools=["read_only_tool"],
        )


    def execute(self, context_bus, task=None, **kwargs):
        return None


class PermissionAgentTests(unittest.TestCase):

    def test_policy_allows_and_denies_tools(self):
        policy = PermissionPolicy.from_lists(allowed_tools=["read_only_tool"], denied_tools=["filesystem:write"])
        self.assertTrue(policy.permits_tool("read_only_tool"))
        self.assertFalse(policy.permits_tool("filesystem:write"))
        self.assertFalse(policy.permits_tool("unknown_tool"))


    def test_base_agent_uses_allowed_tools(self):
        agent = DummyPermissionAgent()
        self.assertTrue(agent.can_use_tool("read_only_tool"))
        self.assertFalse(agent.can_use_tool("filesystem:write"))
        self.assertEqual(agent.describe().allowed_tools, ["read_only_tool"])
        self.assertEqual(agent.describe().denied_tools, [])


if __name__ == "__main__":
    unittest.main()
