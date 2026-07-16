import unittest

from helpers import install_dummy_ollama


install_dummy_ollama()

from normalizer import Normalizer


class NormalizerTests(unittest.TestCase):

    def setUp(self):
        self.normalizer = Normalizer()


    def test_normalizes_known_key_synonyms(self):
        fact = self.normalizer.normalize_fact(
            {
                "category": "interest",
                "key": "favorite_band",
                "value": "Metallica"
            }
        )

        self.assertEqual(fact["category"], "Interessen")
        self.assertEqual(fact["key"], "Lieblingsband")
        self.assertEqual(fact["value"], "Metallica")


    def test_normalizes_other_known_synonyms(self):
        fact = self.normalizer.normalize_fact(
            {
                "category": "skills",
                "key": "favorite book",
                "value": " Das Parfum "
            }
        )

        self.assertEqual(fact["category"], "Fähigkeiten")
        self.assertEqual(fact["key"], "Lieblingsbuch")
        self.assertEqual(fact["value"], "Das Parfum")


    def test_leaves_unknown_values_unchanged(self):
        fact = self.normalizer.normalize_fact(
            {
                "category": "custom_category",
                "key": "custom_key",
                "value": "Custom Value"
            }
        )

        self.assertEqual(fact["category"], "custom_category")
        self.assertEqual(fact["key"], "custom_key")
        self.assertEqual(fact["value"], "Custom Value")


if __name__ == "__main__":
    unittest.main()
