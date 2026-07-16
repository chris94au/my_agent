import unittest

from research.source_ranker import SourceRanker


class SourceRankerTests(unittest.TestCase):

    def setUp(self):
        self.ranker = SourceRanker()


    def test_ranks_reliable_and_relevant_sources_higher(self):
        sources = [
            {
                "title": "Hamburg Restaurant Guide",
                "url": "https://falstaff.com/hamburg-restaurants",
                "snippet": "Bewertete Restaurants in Hamburg",
                "content": "Fine dining, ratings and detailed notes."
            },
            {
                "title": "Generic Blog",
                "url": "https://example.net/post",
                "snippet": "Random blog post",
                "content": "Short and weak content."
            },
        ]

        ranked = self.ranker.rank_sources("beste restaurants hamburg", sources, limit=2)

        self.assertEqual(ranked[0]["url"], "https://falstaff.com/hamburg-restaurants")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])
        self.assertGreater(ranked[0]["reliability"], ranked[1]["reliability"])
        self.assertGreater(ranked[0]["relevance"], 0.5)


    def test_scores_include_completeness_and_freshness(self):
        sources = [
            {
                "title": "Updated Guide",
                "url": "https://wikipedia.org/wiki/Hamburg",
                "snippet": "Longer article",
                "content": "A" * 1200,
                "published_at": "2026-07-15T10:00:00+00:00",
            }
        ]

        ranked = self.ranker.rank_sources("Hamburg", sources, limit=1)
        item = ranked[0]
        self.assertIn("freshness", item)
        self.assertIn("completeness", item)
        self.assertGreaterEqual(item["score"], 0.0)
        self.assertLessEqual(item["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
