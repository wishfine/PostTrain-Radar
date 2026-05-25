import unittest
import os
from src.keyword_filter import KeywordFilter

class TestKeywordFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure we run tests relative to the root containing config/
        cls.filter = KeywordFilter("config/keywords.yaml")

    def test_positive_candidate(self):
        title = "Direct Preference Optimization: Your Language Model is Secretly a Reward Model"
        abstract = "We present DPO to align large language models with human preferences."
        res = self.filter.check_paper(title, abstract)
        self.assertTrue(res["is_candidate"])
        self.assertIn("dpo", res["keywords_matched"])
        self.assertIn("language model", res["keywords_matched"])

    def test_negative_no_posttrain(self):
        title = "Pre-training Large Vision-Language Models from Scratch"
        abstract = "We pretrain a multimodal model on 10 billion web tokens."
        res = self.filter.check_paper(title, abstract)
        self.assertFalse(res["is_candidate"])

    def test_negative_no_llm(self):
        title = "Optimizing policy gradient in gridworlds"
        abstract = "We present reward modeling optimization for simple environment agents."
        res = self.filter.check_paper(title, abstract)
        self.assertFalse(res["is_candidate"])

if __name__ == "__main__":
    unittest.main()
