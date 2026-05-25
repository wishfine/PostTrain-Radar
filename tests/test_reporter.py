import unittest
from src.reporter import ReportGenerator

class TestReporter(unittest.TestCase):
    def test_report_generation(self):
        papers = [
            {
                "title": "Paper High",
                "venue": "ICLR",
                "year": 2025,
                "is_candidate": 1,
                "is_relevant": 1,
                "model_type": "LLM",
                "post_training_types": ["DPO / Preference Optimization"],
                "problem_tags": ["Length Bias"],
                "keywords_matched": ["dpo", "llm"],
                "confidence": 0.90,
                "reason": "Highly relevant DPO paper",
                "paper_url": "http://example.com/high",
                "pdf_url": "http://example.com/high.pdf"
            },
            {
                "title": "Paper Med",
                "venue": "ICLR",
                "year": 2025,
                "is_candidate": 1,
                "is_relevant": 1,
                "model_type": "VLM",
                "post_training_types": ["Visual Instruction Tuning"],
                "problem_tags": ["Multimodal Hallucination"],
                "keywords_matched": ["vlm", "instruction tuning"],
                "confidence": 0.75,
                "reason": "Medium relevance VLM paper",
                "paper_url": "http://example.com/med",
                "pdf_url": "http://example.com/med.pdf"
            }
        ]
        
        reporter = ReportGenerator("ICLR", 2025)
        report_md = reporter.generate(papers)
        
        self.assertIn("# PostTrain Radar Report: ICLR 2025", report_md)
        self.assertIn("Total papers: 2", report_md)
        self.assertIn("Relevant post-training papers: 2", report_md)
        
        # Check Priority Headings
        self.assertIn("### High Priority", report_md)
        self.assertIn("### Medium Priority", report_md)
        self.assertIn("### Low Priority", report_md)
        
        # Check specific papers placement
        self.assertIn("Paper High", report_md)
        self.assertIn("Paper Med", report_md)

if __name__ == "__main__":
    unittest.main()
