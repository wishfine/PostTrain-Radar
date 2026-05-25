import unittest
import tempfile
import shutil
import os
import yaml
import json
from unittest.mock import patch, MagicMock

from src.app import PostTrainRadarApp
from src.database import DatabaseManager
from src.classifier import RuleClassifier
from src.note_generator import NoteGenerator
from src.share_generator import ShareGenerator
from src.knowledge_backflow import KnowledgeBackflow
from src.exporters.markdown_exporter import MarkdownExporter

class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Create temp directory structure for integration tests
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_posttrain.db")
        self.overrides_path = os.path.join(self.test_dir, "test_overrides.yaml")
        
        # Write basic overrides config
        self.overrides_data = {
            "test_source_id_123": {
                "priority": "High",
                "reading_status": "Reading",
                "model_type": "Agent",
                "post_training_types": ["GRPO / Reasoning RL"],
                "problem_tags": ["Length Bias"],
                "data_origin": "manual_import"
            },
            "custom overrides target title": {
                "priority": "High",
                "reading_status": "Finished",
                "post_training_types": ["DPO / Preference Optimization"],
                "problem_tags": ["Reward Hacking"]
            }
        }
        with open(self.overrides_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.overrides_data, f)

    def tearDown(self):
        # Clean up temp files
        shutil.rmtree(self.test_dir)

    def test_database_migrations_and_origins(self):
        # 1. Test database migration & data origin behavior
        db = DatabaseManager(self.db_path)
        
        # Test insert paper with data origin
        paper = {
            "title": "A Test Paper on DPO",
            "title_norm": "a test paper on dpo",
            "abstract": "We study direct preference optimization.",
            "abstract_hash": "abc123hash",
            "authors": ["Author One", "Author Two"],
            "venue": "ICLR",
            "year": 2025,
            "paper_url": "http://test.url",
            "pdf_url": "http://test.pdf",
            "source": "openreview",
            "source_id": "test_src_99",
            "status": "accepted",
            "data_origin": "openreview_api"
        }
        paper_id = db.insert_or_update_paper(paper)
        
        # Retrieve and verify data_origin column exists and is correctly populated
        papers = db.get_classified_papers("ICLR", 2025)
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["data_origin"], "openreview_api")
        
        # Verify matched_evidence column exists in paper_tags table
        tag_data = {
            "is_candidate": 1,
            "is_relevant": 1,
            "model_type": "LLM",
            "post_training_types": ["DPO / Preference Optimization"],
            "problem_tags": ["Length Bias"],
            "keywords_matched": ["dpo"],
            "confidence": 0.85,
            "reason": "Test reason",
            "matched_evidence": {
                "post_training_types": {
                    "DPO / Preference Optimization": ["dpo"]
                }
            }
        }
        db.update_paper_tags(paper_id, tag_data)
        
        papers_tagged = db.get_classified_papers("ICLR", 2025)
        self.assertEqual(len(papers_tagged), 1)
        self.assertEqual(papers_tagged[0]["matched_evidence"], {
            "post_training_types": {
                "DPO / Preference Optimization": ["dpo"]
            }
        })
        db.close()

    def test_overrides_matching(self):
        # 2. Test overrides matching by title or source_id
        db = DatabaseManager(self.db_path)
        classifier = RuleClassifier(config_path="config/categories.yaml", overrides_path=self.overrides_path)
        
        # Test override match by source_id
        res_by_id = classifier.classify(
            title="Some Random Title",
            abstract="Some abstract mentioning reinforcement learning",
            source_id="test_source_id_123"
        )
        self.assertEqual(res_by_id["model_type"], "Agent")
        self.assertEqual(res_by_id["priority"], "High")
        self.assertEqual(res_by_id["reading_status"], "Reading")
        self.assertEqual(res_by_id["post_training_types"], ["GRPO / Reasoning RL"])
        self.assertEqual(res_by_id["problem_tags"], ["Length Bias"])
        self.assertEqual(res_by_id["data_origin"], "manual_import")
        
        # Test override match by title_norm
        res_by_title = classifier.classify(
            title="Custom Overrides Target Title",
            abstract="Abstract content",
            source_id="other_id"
        )
        self.assertEqual(res_by_title["priority"], "High")
        self.assertEqual(res_by_title["reading_status"], "Finished")
        self.assertEqual(res_by_title["post_training_types"], ["DPO / Preference Optimization"])
        self.assertEqual(res_by_title["problem_tags"], ["Reward Hacking"])
        
        db.close()

    def test_file_merges_preservation_of_human_notes(self):
        # 3. Test preservation of human notes for NoteGenerator and ShareGenerator
        note_gen = NoteGenerator()
        share_gen = ShareGenerator()
        
        paper = {
            "title": "A Test Paper on DPO",
            "venue": "ICLR",
            "year": 2025,
            "authors": ["Author A"],
            "model_type": "LLM",
            "post_training_types": ["DPO / Preference Optimization"],
            "problem_tags": ["Length Bias"],
            "data_origin": "openreview_api",
            "is_relevant": 1,
            "confidence": 0.85,
            "reason": "Test reason",
            "keywords_matched": ["dpo"],
            "matched_evidence": {
                "post_training_types": {
                    "DPO / Preference Optimization": ["dpo"]
                }
            }
        }
        
        # Generate initial note
        initial_note = note_gen.generate(paper)
        self.assertIn("### 这篇论文想解决什么问题？", initial_note)
        self.assertIn("<!-- START_MY_NOTES -->", initial_note)
        
        # Simulate user writing notes
        modified_note = initial_note.replace(
            "用我自己的话写，而不是复制摘要。",
            "My custom human comments on this paper."
        )
        modified_note = modified_note.replace(
            "从以下角度批判性分析：",
            "My custom judgment comments."
        )
        
        # Run merge generation (with existing content)
        updated_paper = paper.copy()
        updated_paper["priority"] = "High"  # Changed priority
        updated_paper["my_rating"] = "5 Stars"
        
        merged_note = note_gen.generate(updated_paper, existing_content=modified_note)
        
        # Check that metadata got updated
        self.assertIn("- Priority: High", merged_note)
        self.assertIn("- My Rating: 5 Stars", merged_note)
        # Check that human notes are preserved
        self.assertIn("My custom human comments on this paper.", merged_note)
        self.assertIn("My custom judgment comments.", merged_note)
        self.assertNotIn("用我自己的话写，而不是复制摘要。", merged_note)

        # Test Share Brief merges
        initial_share = share_gen.generate(paper)
        self.assertIn("<!-- START_MY_SHARE_DETAILS -->", initial_share)
        
        modified_share = initial_share.replace(
            "这篇论文主要讲：",
            "Human share details."
        )
        merged_share = share_gen.generate(updated_paper, existing_content=modified_share)
        self.assertIn("Human share details.", merged_share)
        self.assertNotIn("这篇论文主要讲：", merged_share)

    def test_backflow_suggestions(self):
        # 4. Test backflow suggestions generation
        backflow = KnowledgeBackflow(output_dir=self.test_dir)
        
        papers = [
            {
                "title": "A Test Paper on DPO",
                "venue": "ICLR",
                "year": 2025,
                "authors": ["Author A"],
                "model_type": "LLM",
                "post_training_types": ["DPO / Preference Optimization"],
                "problem_tags": ["Length Bias"],
                "data_origin": "openreview_api",
                "is_relevant": 1,
                "confidence": 0.85,
                "reason": "Test reason",
                "keywords_matched": ["dpo"],
                "matched_evidence": {"post_training_types": {"DPO / Preference Optimization": ["dpo"]}}
            },
            {
                "title": "A Test Paper on Agent and VLM",
                "venue": "ICLR",
                "year": 2025,
                "authors": ["Author B"],
                "model_type": "VLM",
                "post_training_types": ["SFT / Instruction Tuning"],
                "problem_tags": ["Length Bias", "Multimodal Hallucination"],
                "data_origin": "openreview_api",
                "is_relevant": 1,
                "confidence": 0.90,
                "reason": "Test reason 2",
                "keywords_matched": ["vlm", "sft"],
                "matched_evidence": {"post_training_types": {"SFT / Instruction Tuning": ["sft"]}}
            }
        ]
        
        res = backflow.run(papers)
        self.assertTrue(os.path.exists(res["suggestions_path"]))
        self.assertEqual(res["patches_count"], 6)  # Topics: LLM, VLM; Methods: DPO, SFT; Problems: Length Bias, Multimodal Hallucination
        
        # Verify patches exist
        patches_dir = os.path.join(self.test_dir, "knowledge_patches")
        self.assertTrue(os.path.exists(os.path.join(patches_dir, "Topics", "LLM_PostTraining.md")))
        self.assertTrue(os.path.exists(os.path.join(patches_dir, "Topics", "VLM_PostTraining.md")))
        self.assertTrue(os.path.exists(os.path.join(patches_dir, "Methods", "DPO.md")))
        self.assertTrue(os.path.exists(os.path.join(patches_dir, "Methods", "SFT.md")))
        
        # Read a patch and verify content
        with open(os.path.join(patches_dir, "Methods", "DPO.md"), "r", encoding="utf-8") as f:
            patch_content = f.read()
        self.assertIn("A Test Paper on DPO", patch_content)

    def test_dry_run_simulation(self):
        # 5. Test dry-run behavior where files are not written to output_dir
        temp_out = os.path.join(self.test_dir, "dry_run_output")
        exporter = MarkdownExporter(output_dir=temp_out, dry_run=True)
        
        paper = {
            "title": "A Dry Run Test Paper",
            "venue": "ICLR",
            "year": 2025,
            "authors": ["Author A"],
            "model_type": "LLM",
            "post_training_types": ["DPO / Preference Optimization"],
            "problem_tags": ["Length Bias"],
            "data_origin": "openreview_api"
        }
        
        # Try note, share, and report exports in dry run mode
        exporter.export_paper_note(paper, "Note content", overwrite=True)
        exporter.export_share_brief(paper, "Share content", overwrite=True)
        exporter.export_report("Test_Report", "Report content", overwrite=True)
        exporter.export_report_at_path("/00_Index/Reading_Queue", "Queue content", overwrite=True)
        
        # Assert directory does not even get created or is empty
        if os.path.exists(temp_out):
            files = []
            for root, dirs, filenames in os.walk(temp_out):
                for f in filenames:
                    files.append(os.path.join(root, f))
            self.assertEqual(len(files), 0, f"Expected no files in dry run output directory, but found: {files}")

if __name__ == "__main__":
    unittest.main()
