import unittest

from helpers import install_dummy_ollama


ollama = install_dummy_ollama()

from critic import Critic


class CriticTests(unittest.TestCase):

    def setUp(self):
        self.critic = Critic(model="test-model")


    def test_critic_falls_back_on_invalid_json(self):
        original_chat = ollama.chat

        def fake_chat(model, messages):
            return {"message": {"content": "keine json antwort"}}

        ollama.chat = fake_chat
        try:
            critique = self.critic.review(
                user_input="Sag hallo",
                memory_context="",
                plan=type("Plan", (), {"steps": []})(),
                step_results=[],
                final_answer="Hallo"
            )
        finally:
            ollama.chat = original_chat

        self.assertTrue(critique.valid)
        self.assertEqual(critique.verdict, "pass")
        self.assertEqual(critique.summary, "Hallo")


    def test_critic_parses_structured_review(self):
        original_chat = ollama.chat

        def fake_chat(model, messages):
            return {
                "message": {
                    "content": """
                    {
                      "verdict": "warn",
                      "summary": "Antwort ist brauchbar, aber kurz.",
                      "risks": ["Fehlende Details"],
                      "improvements": ["Mehr Kontext geben"],
                      "confidence": 0.82,
                      "should_retry": false
                    }
                    """
                }
            }

        ollama.chat = fake_chat
        try:
            critique = self.critic.review(
                user_input="Erkläre den Plan",
                memory_context="",
                plan=type("Plan", (), {"steps": []})(),
                step_results=[{"action": "respond", "status": "ok", "result": "Kurz"}],
                final_answer="Kurz"
            )
        finally:
            ollama.chat = original_chat

        self.assertTrue(critique.valid)
        self.assertEqual(critique.verdict, "warn")
        self.assertEqual(critique.summary, "Antwort ist brauchbar, aber kurz.")
        self.assertEqual(critique.risks, ["Fehlende Details"])
        self.assertEqual(critique.improvements, ["Mehr Kontext geben"])
        self.assertAlmostEqual(critique.confidence, 0.82, places=2)
        self.assertFalse(critique.should_retry)


if __name__ == "__main__":
    unittest.main()
