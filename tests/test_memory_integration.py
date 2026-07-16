import unittest

from helpers import install_dummy_ollama


install_dummy_ollama()

from normalizer import Normalizer
from research.memory_integration import ResearchMemoryIntegrator


class FakeMemory:

    def __init__(self):
        self.fact_calls = []
        self.summary_calls = []


    def save_fact(self, **kwargs):
        self.fact_calls.append(kwargs)
        return {"status": "inserted"}


    def save_summary(self, *args, **kwargs):
        self.summary_calls.append((args, kwargs))
        return {"status": "inserted"}


class FakeValidator:

    def validate(self, memory, conversation=None):
        return {"approved": True, "importance": 8, "confidence": 0.92}


class MemoryIntegrationTests(unittest.TestCase):

    def test_persists_user_preferences_but_skips_generic_research(self):
        memory = FakeMemory()
        integrator = ResearchMemoryIntegrator(
            memory=memory,
            normalizer=Normalizer(),
            validator=FakeValidator(),
        )

        saved = integrator.persist(
            "Ich bevorzuge italienische Restaurants in Hamburg",
            {
                "summary": "Italienische Restaurants in Hamburg sind beliebt.",
                "confidence": 0.9,
            },
        )
        self.assertTrue(saved)
        self.assertEqual(len(memory.fact_calls), 1)
        self.assertEqual(memory.fact_calls[0]["category"], "Präferenzen")
        self.assertIn("italienische Restaurants in Hamburg", memory.fact_calls[0]["value"])

        saved_generic = integrator.persist(
            "Welche Restaurants sind in Hamburg gut?",
            {
                "summary": "Ein Restaurant ist gut bewertet.",
                "confidence": 0.8,
            },
        )
        self.assertEqual(saved_generic, [])
        self.assertEqual(len(memory.fact_calls), 1)
        self.assertEqual(len(memory.summary_calls), 0)


if __name__ == "__main__":
    unittest.main()
