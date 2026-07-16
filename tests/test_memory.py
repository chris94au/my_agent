import json
import unittest

from helpers import install_dummy_ollama


install_dummy_ollama()

from memory import Memory


class MemoryTests(unittest.TestCase):

    def setUp(self):
        self.memory = Memory(":memory:")


    def tearDown(self):
        self.memory.close()


    def _insert_fact_raw(self, category, key, value, importance, confidence):
        embedding = self.memory.embedder.create(
            f"{category}: {key}: {value}"
        )
        self.memory.connection.execute(
            """
            INSERT INTO facts
            (category, key, value, importance, confidence, status, occurrence_count, use_count, embedding)
            VALUES (?, ?, ?, ?, ?, 'active', 1, 0, ?)
            """,
            (
                category,
                key,
                value,
                importance,
                confidence,
                json.dumps(embedding)
            )
        )
        self.memory.connection.commit()


    def _insert_summary_raw(self, topic, summary, importance, confidence):
        embedding = self.memory.embedder.create(
            f"{topic}: {summary}"
        )
        self.memory.connection.execute(
            """
            INSERT INTO summaries
            (topic, summary, importance, confidence, status, occurrence_count, use_count, embedding)
            VALUES (?, ?, ?, ?, 'active', 1, 0, ?)
            """,
            (
                topic,
                summary,
                importance,
                confidence,
                json.dumps(embedding)
            )
        )
        self.memory.connection.commit()


    def test_repeated_fact_increases_importance_without_exceeding_maximum(self):
        self.memory.save_fact(
            "interest",
            "favorite_band",
            "Metallica",
            importance=7,
            confidence=0.9
        )
        self.memory.save_fact(
            "interest",
            "favorite_band",
            "Metallica",
            importance=7,
            confidence=0.9
        )
        self.memory.save_fact(
            "interest",
            "favorite_band",
            "Metallica",
            importance=7,
            confidence=0.9
        )
        self.memory.save_fact(
            "interest",
            "favorite_band",
            "Metallica",
            importance=7,
            confidence=0.9
        )

        facts = self.memory.get_all_facts()
        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact["occurrence_count"], 4)
        self.assertGreaterEqual(fact["importance"], 8)
        self.assertLessEqual(fact["importance"], 10)
        self.assertGreaterEqual(fact["confidence"], 0.9)


    def test_retrieval_uses_importance_confidence_and_recency(self):
        self._insert_fact_raw(
            "interest",
            "favorite_band",
            "Metallica",
            importance=9,
            confidence=0.95
        )
        self._insert_fact_raw(
            "interest",
            "band_note",
            "Metallica",
            importance=5,
            confidence=0.4
        )

        results = self.memory.get_relevant_memories(
            "Metallica",
            limit=5
        )

        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0]["importance"], 9)
        self.assertAlmostEqual(results[0]["confidence"], 0.95, places=2)
        self.assertGreater(results[0]["final_score"], results[1]["final_score"])


    def test_summary_storage_is_separate_from_facts(self):
        self.memory.save_fact(
            "interest",
            "instrument",
            "Gitarre",
            importance=8,
            confidence=0.9
        )
        self.memory.save_summary(
            "Gitarrenmusik",
            "Der Benutzer interessiert sich stark für Gitarrenmusik und spielt selbst Gitarre.",
            importance=6,
            confidence=0.8
        )

        self.assertEqual(len(self.memory.get_all_facts()), 1)
        self.assertEqual(len(self.memory.get_all_summaries()), 1)

        context = self.memory.get_semantic_context("Gitarrenmusik")
        self.assertIn("Zusammenfassung", context)
        self.assertIn("Gitarre", context)


    def test_low_value_memory_can_be_archived_instead_of_deleted(self):
        self._insert_fact_raw(
            "state",
            "current_food",
            "Pizza",
            importance=2,
            confidence=0.3
        )
        self.memory.connection.execute(
            """
            UPDATE facts
            SET last_seen_at = '2000-01-01 00:00:00',
                last_used_at = '2000-01-01 00:00:00'
            WHERE key = 'current_food'
            """
        )
        self.memory.connection.commit()

        archived = self.memory.archive_low_value_memories()
        facts = self.memory.get_all_facts(include_archived=True)
        self.assertTrue(archived)
        self.assertEqual(facts[0]["status"], "archived")
        self.assertIsNotNone(facts[0]["archived_at"])


if __name__ == "__main__":
    unittest.main()
