import unittest

from research.synthesizer import ResearchSynthesizer


class SynthesizerTests(unittest.TestCase):

    def setUp(self):
        self.synthesizer = ResearchSynthesizer()


    def test_merges_sources_and_marks_contradictions(self):
        sources = [
            {
                "url": "https://source-a.example",
                "rank_score": 0.9,
                "reliability": 0.9,
                "relevance": 0.8,
                "extracted": {
                    "facts": [
                        {
                            "name": "Restaurant Beispiel",
                            "location": "Hamburg",
                            "rating": 4.8,
                            "category": "Fine Dining",
                            "source": "https://source-a.example",
                            "evidence": "Source A",
                            "confidence": 0.9,
                        }
                    ]
                },
            },
            {
                "url": "https://source-b.example",
                "rank_score": 0.7,
                "reliability": 0.8,
                "relevance": 0.7,
                "extracted": {
                    "facts": [
                        {
                            "name": "Restaurant Beispiel",
                            "location": "Hamburg",
                            "rating": 4.2,
                            "category": "Fine Dining",
                            "source": "https://source-b.example",
                            "evidence": "Source B",
                            "confidence": 0.75,
                        }
                    ]
                },
            },
        ]

        result = self.synthesizer.synthesize(
            query="Welche Restaurants sind gut?",
            memory_context="Benutzer mag Empfehlungen mit hoher Qualität.",
            sources=sources,
        )

        self.assertIn("Restaurant Beispiel", result["answer"])
        self.assertEqual(len(result["sources_used"]), 2)
        self.assertTrue(result["citations"])
        self.assertTrue(result["contradictions"])
        self.assertGreater(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)
        self.assertIn("Widersprüche", result["answer"])


if __name__ == "__main__":
    unittest.main()
