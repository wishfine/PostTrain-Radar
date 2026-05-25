import unittest
from src.deduplicator import Deduplicator
from src.normalizer import normalize_title

class TestDeduplicator(unittest.TestCase):
    def setUp(self):
        self.dedup = Deduplicator(threshold=90.0)
        self.existing = [
            {
                "title": "Direct Preference Optimization: Your Language Model is Secretly a Reward Model",
                "title_norm": normalize_title("Direct Preference Optimization: Your Language Model is Secretly a Reward Model")
            },
            {
                "title": "DeepSeekMath: Pushing the Limits of Mathematical Reasoning",
                "title_norm": normalize_title("DeepSeekMath: Pushing the Limits of Mathematical Reasoning")
            }
        ]

    def test_exact_duplicate(self):
        new_paper = {
            "title": "Direct Preference Optimization: Your Language Model is Secretly a Reward Model.",
            "title_norm": normalize_title("Direct Preference Optimization: Your Language Model is Secretly a Reward Model.")
        }
        dup = self.dedup.find_duplicate(new_paper, self.existing)
        self.assertIsNotNone(dup)
        self.assertEqual(dup["title"], self.existing[0]["title"])

    def test_fuzzy_duplicate(self):
        # Slightly modified title
        new_paper = {
            "title": "Direct Preference Optimization: Your LLM is Secretly a Reward Model",
            "title_norm": normalize_title("Direct Preference Optimization: Your LLM is Secretly a Reward Model")
        }
        dup = self.dedup.find_duplicate(new_paper, self.existing)
        self.assertIsNotNone(dup)
        self.assertEqual(dup["title"], self.existing[0]["title"])

    def test_non_duplicate(self):
        new_paper = {
            "title": "SimPO: Simple Preference Optimization with a Reference-Free Reward",
            "title_norm": normalize_title("SimPO: Simple Preference Optimization with a Reference-Free Reward")
        }
        dup = self.dedup.find_duplicate(new_paper, self.existing)
        self.assertIsNull = self.assertIsNone(dup) # Use standard assertIsNone

if __name__ == "__main__":
    unittest.main()
