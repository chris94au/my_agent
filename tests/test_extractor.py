import unittest

from helpers import install_dummy_ollama


ollama = install_dummy_ollama()

from research.extractor import ResearchExtractor


class ExtractorTests(unittest.TestCase):

    def setUp(self):
        self.extractor = ResearchExtractor(model="test-model")


    def test_extracts_validated_facts_from_structured_json(self):
        original_chat = ollama.chat

        def fake_chat(model, messages):
            return {
                "message": {
                    "content": """
                    {
                      "summary": "Restaurantquelle mit Bewertung",
                      "confidence": 0.88,
                      "facts": [
                        {
                          "name": "Restaurant Beispiel",
                          "location": "Hamburg",
                          "rating": 4.8,
                          "category": "Fine Dining",
                          "source": "https://example.com",
                          "evidence": "Restaurant Beispiel wird mit 4.8 bewertet.",
                          "confidence": 0.91
                        }
                      ]
                    }
                    """
                }
            }

        ollama.chat = fake_chat
        try:
            extracted = self.extractor.extract(
                query="Welche Restaurants sind gut?",
                source={
                    "url": "https://example.com",
                    "title": "Example Restaurant",
                    "content": "Restaurant Beispiel wird mit 4.8 bewertet.",
                },
            )
        finally:
            ollama.chat = original_chat

        self.assertEqual(extracted["status"], "ok")
        self.assertEqual(extracted["summary"], "Restaurantquelle mit Bewertung")
        self.assertEqual(len(extracted["facts"]), 1)
        fact = extracted["facts"][0]
        self.assertEqual(fact["name"], "Restaurant Beispiel")
        self.assertEqual(fact["location"], "Hamburg")
        self.assertAlmostEqual(fact["rating"], 4.8, places=1)
        self.assertEqual(fact["category"], "Fine Dining")
        self.assertEqual(fact["source"], "https://example.com")
        self.assertAlmostEqual(fact["confidence"], 0.91, places=2)


    def test_falls_back_when_json_is_invalid(self):
        original_chat = ollama.chat

        def fake_chat(model, messages):
            return {"message": {"content": "not json"}}

        ollama.chat = fake_chat
        try:
            extracted = self.extractor.extract(
                query="Welche Restaurants sind gut?",
                source={
                    "url": "https://example.com",
                    "title": "Example Restaurant",
                    "content": "Fallback content.",
                },
            )
        finally:
            ollama.chat = original_chat

        self.assertEqual(extracted["status"], "ok")
        self.assertTrue(extracted["facts"])
        self.assertEqual(extracted["facts"][0]["category"], "source_excerpt")
        self.assertEqual(extracted["summary"], "Example Restaurant")


if __name__ == "__main__":
    unittest.main()
