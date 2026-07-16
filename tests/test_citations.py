import unittest

from research.citations import CitationTracker


class CitationTests(unittest.TestCase):

    def test_records_claims_with_timestamp_and_confidence(self):
        tracker = CitationTracker()
        record = tracker.record(
            claim="Restaurant Beispiel hat 4.8 Sterne",
            source="https://example.com",
            confidence=0.9,
            metadata={"query": "Restaurants"},
        )

        self.assertEqual(record.claim, "Restaurant Beispiel hat 4.8 Sterne")
        self.assertEqual(record.source, "https://example.com")
        self.assertAlmostEqual(record.confidence, 0.9, places=2)
        self.assertTrue(record.timestamp)
        self.assertEqual(record.metadata["query"], "Restaurants")

        context = tracker.as_context()
        self.assertIn("Quellenverfolgung", context)
        self.assertIn("Restaurant Beispiel hat 4.8 Sterne", context)


if __name__ == "__main__":
    unittest.main()
