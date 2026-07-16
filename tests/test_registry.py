import os
import sqlite3
import tempfile
import unittest

from helpers import install_dummy_ollama


install_dummy_ollama()

from tools.filesystem import read_file
from tools.registry import Tool, ToolParameter, ToolRegistry


class RegistryTests(unittest.TestCase):

    def test_validate_call_requires_parameters(self):
        registry = ToolRegistry(audit_db_path=os.path.join(tempfile.gettempdir(), "registry-test.db"))
        registry.register(
            Tool(
                name="adder",
                description="Adds numbers.",
                parameters=[
                    ToolParameter(name="a", type="number", required=True),
                    ToolParameter(name="b", type="number", required=True),
                ],
                execute_fn=lambda data: data["a"] + data["b"],
                permission="math",
                accepts_scalar=False,
            )
        )

        valid, normalized, issues = registry.validate_call(
            "adder",
            {"a": 1, "b": 2}
        )
        self.assertTrue(valid)
        self.assertEqual(normalized, {"a": 1, "b": 2})
        self.assertEqual(issues, [])

        valid, normalized, issues = registry.validate_call(
            "adder",
            {"a": 1}
        )
        self.assertFalse(valid)
        self.assertIn("Missing required parameter: b", issues)


    def test_execute_logs_successful_calls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_db = os.path.join(tmpdir, "tool-events.db")
            registry = ToolRegistry(audit_db_path=audit_db)
            registry.register(
                Tool(
                    name="adder",
                    description="Adds numbers.",
                    parameters=[
                        ToolParameter(name="a", type="number", required=True),
                        ToolParameter(name="b", type="number", required=True),
                    ],
                    execute_fn=lambda data: data["a"] + data["b"],
                    permission="math",
                    accepts_scalar=False,
                )
            )

            success, result = registry.execute(
                "adder",
                {"a": 2, "b": 3},
                agent="test-agent"
            )

            self.assertTrue(success)
            self.assertEqual(result, 5)

            connection = sqlite3.connect(audit_db)
            rows = connection.execute(
                "SELECT agent, tool, status FROM tool_events"
            ).fetchall()
            connection.close()

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "test-agent")
            self.assertEqual(rows[0][1], "adder")
            self.assertEqual(rows[0][2], "ok")


    def test_filesystem_read_rejects_path_traversal(self):
        result = read_file("../secret.txt")
        self.assertIn("Fehler beim Lesen", result)


if __name__ == "__main__":
    unittest.main()
