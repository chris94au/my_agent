import json
import unittest

from helpers import install_dummy_ollama


install_dummy_ollama()

from research.pipeline import ResearchPipeline


class ResearchPipelineTests(unittest.TestCase):

    def test_pipeline_searches_fetches_and_synthesizes_context(self):
        search_payload = json.dumps(
            {
                "query": "beste restaurants hamburg",
                "results": [
                    {
                        "title": "Falstaff Hamburg",
                        "url": "https://falstaff.example/hamburg",
                        "snippet": "Bewertete Restaurants in Hamburg"
                    },
                    {
                        "title": "Restaurant Guide",
                        "url": "https://guide.example/restaurants",
                        "snippet": "Empfehlungen und Bewertungen"
                    }
                ]
            },
            ensure_ascii=False
        )

        def fake_search(data):
            self.assertEqual(data["query"], "beste restaurants hamburg")
            return search_payload

        def fake_fetch(data):
            url = data["url"]
            return {
                "status": "ok",
                "url": url,
                "final_url": url,
                "title": f"Title for {url}",
                "content": f"<html><body><h1>{url}</h1><p>Restaurant A 4.8/5</p></body></html>",
            }

        class FakeExtractor:
            def extract(self, query, source):
                return {
                    "status": "ok",
                    "summary": "Extrahierte Restaurantdaten",
                    "confidence": 0.9,
                    "facts": [
                        {
                            "name": "Restaurant A",
                            "location": "Hamburg",
                            "rating": 4.8,
                            "category": "Restaurant",
                            "source": source["url"],
                            "evidence": "Restaurant A 4.8/5",
                            "confidence": 0.9,
                        }
                    ],
                    "validated": True,
                    "warnings": [],
                    "source": source["url"],
                }

        pipeline = ResearchPipeline(searcher=fake_search, fetcher=fake_fetch, extractor=FakeExtractor())
        result = pipeline.run(
            "beste restaurants hamburg",
            memory_context="Benutzer mag gute italienische Restaurants",
            limit=2,
        )

        self.assertEqual(result.query, "beste restaurants hamburg")
        self.assertEqual(len(result.sources_used), 2)
        self.assertGreater(result.confidence, 0)
        self.assertIn("Research Summary", result.research_context)
        self.assertIn("Vorwissen", result.research_context)
        self.assertIn("Restaurant A", result.research_context)
        self.assertTrue(result.citations)
        self.assertTrue(all("source" in citation for citation in result.citations))
        self.assertIn("Quellenverfolgung", result.citation_context)


if __name__ == "__main__":
    unittest.main()
