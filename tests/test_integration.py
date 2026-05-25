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
                "relevance_level": "A_Core_PostTraining",
                "include_in_reading_queue": 1,
                "include_in_knowledge_patches": 1,
                "reviewer_comment": "Manual reviewer override comment.",
                "data_origin": "manual_import"
            },
            "custom overrides target title": {
                "priority": "High",
                "reading_status": "Finished",
                "relevance_level": "B_Related_LLM_VLM_Training_or_Evaluation"
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
        
        # Verify matched_evidence column and relevance level columns exist in paper_tags table
        tag_data = {
            "is_candidate": 1,
            "is_relevant": 1,
            "relevance_level": "A_Core_PostTraining",
            "is_core_posttraining": 1,
            "model_type": "LLM",
            "post_training_types": ["DPO / Preference Optimization"],
            "problem_tags": ["Length Bias"],
            "keywords_matched": ["dpo"],
            "confidence": 0.85,
            "reason": "Test reason",
            "matched_evidence": {
                "post_training_types": [
                    {
                        "keyword_group": "DPO / Preference Optimization",
                        "title_matches": ["dpo"],
                        "abstract_matches": [],
                        "reason_text": "Matched title"
                    }
                ]
            }
        }
        db.update_paper_tags(paper_id, tag_data)
        
        papers_tagged = db.get_classified_papers("ICLR", 2025)
        self.assertEqual(len(papers_tagged), 1)
        self.assertEqual(papers_tagged[0]["relevance_level"], "A_Core_PostTraining")
        self.assertEqual(papers_tagged[0]["is_core_posttraining"], 1)
        self.assertEqual(papers_tagged[0]["matched_evidence"]["post_training_types"][0]["keyword_group"], "DPO / Preference Optimization")
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
        self.assertEqual(res_by_id["relevance_level"], "A_Core_PostTraining")
        self.assertEqual(res_by_id["is_core_posttraining"], 1)
        self.assertEqual(res_by_id["include_in_reading_queue"], 1)
        self.assertEqual(res_by_id["reviewer_comment"], "Manual reviewer override comment.")
        
        # Test override match by title_norm
        res_by_title = classifier.classify(
            title="Custom Overrides Target Title",
            abstract="Abstract content",
            source_id="other_id"
        )
        self.assertEqual(res_by_title["priority"], "High")
        self.assertEqual(res_by_title["reading_status"], "Finished")
        self.assertEqual(res_by_title["relevance_level"], "B_Related_LLM_VLM_Training_or_Evaluation")
        self.assertEqual(res_by_title["is_core_posttraining"], 0)
        self.assertEqual(res_by_title["is_relevant"], 1)
        
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
            "relevance_level": "A_Core_PostTraining",
            "is_core_posttraining": 1,
            "confidence": 0.85,
            "reason": "Test reason",
            "keywords_matched": ["dpo"],
            "matched_evidence": {
                "post_training_types": [
                    {
                        "keyword_group": "DPO / Preference Optimization",
                        "title_matches": ["dpo"],
                        "abstract_matches": [],
                        "reason_text": "Matched title"
                    }
                ]
            }
        }
        
        # Generate initial note
        initial_note = note_gen.generate(paper)
        self.assertIn("## [My Reading Notes]", initial_note)
        self.assertIn("<!-- START_MY_READING_NOTES -->", initial_note)
        
        # Simulate user writing notes
        modified_note = initial_note.replace(
            "(在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)",
            "My custom human comments on this paper."
        )
        modified_note = modified_note.replace(
            "(在这里写下您对该文的真实技术评价，是否真正解决了痛点？)",
            "My custom judgment comments."
        )
        
        # Run merge generation (with existing content)
        updated_paper = paper.copy()
        updated_paper["priority"] = "High"  # Changed priority
        updated_paper["my_rating"] = "5 Stars"
        
        merged_note = note_gen.generate(updated_paper, existing_content=modified_note)
        
        # Check that metadata got updated
        self.assertIn("*   **Priority**: High", merged_note)
        self.assertIn("*   **Relevance Level**: A_Core_PostTraining", merged_note)
        # Check that human notes are preserved
        self.assertIn("My custom human comments on this paper.", merged_note)
        self.assertIn("My custom judgment comments.", merged_note)
        self.assertNotIn("(在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)", merged_note)

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

    def test_candidate_not_equal_to_relevant(self):
        # 4. Verify candidate is not always equal to relevant (C or D classes)
        classifier = RuleClassifier(config_path="config/categories.yaml", overrides_path=self.overrides_path)
        
        # C Class paper - LLM app but no tuning/alignment
        res_c = classifier.classify(
            title="Using LLM for Clinical Prediction",
            abstract="We present a study using ChatGPT prompts to extract clinical terms and make medical predictions.",
            source_id="test_c"
        )
        self.assertEqual(res_c["relevance_level"], "C_General_LLM_VLM_Not_PostTraining")
        self.assertEqual(res_c["is_relevant"], 0)
        self.assertEqual(res_c["is_core_posttraining"], 0)
        
        # D Class paper - completely off-topic
        res_d = classifier.classify(
            title="High Performance Database Systems",
            abstract="We present index structures for relational databases to optimize query execution.",
            source_id="test_d"
        )
        self.assertEqual(res_d["relevance_level"], "D_Irrelevant")
        self.assertEqual(res_d["is_relevant"], 0)

    def test_relevance_level_classification(self):
        # 5. Verify relevance level matches category
        classifier = RuleClassifier(config_path="config/categories.yaml", overrides_path=self.overrides_path)
        
        # Core post training (SFT / DPO)
        res_a = classifier.classify(
            title="DPO for Language Model Alignment",
            abstract="We study direct preference optimization as a simple and stable alternative to RLHF.",
            source_id="test_a"
        )
        self.assertEqual(res_a["relevance_level"], "A_Core_PostTraining")
        self.assertEqual(res_a["is_core_posttraining"], 1)
        self.assertEqual(res_a["is_relevant"], 1)

        # Related Training/Evaluation (LoRA / general evaluation)
        res_b = classifier.classify(
            title="LoRA-based Parameter-Efficient Fine-Tuning",
            abstract="We present a parameter-efficient approach applying low-rank adapters.",
            source_id="test_b"
        )
        self.assertEqual(res_b["relevance_level"], "B_Related_LLM_VLM_Training_or_Evaluation")
        self.assertEqual(res_b["is_core_posttraining"], 0)
        self.assertEqual(res_b["is_relevant"], 1)

    def test_false_positive_demotions(self):
        # 6. Verify false positive demotions
        classifier = RuleClassifier(config_path="config/categories.yaml", overrides_path=self.overrides_path)
        
        # Robot Policy without NLP
        res_robot = classifier.classify(
            title="Imitation Learning for Robotic Manipulation",
            abstract="We present a robot control policy optimized using continuous trajectory predictions.",
            source_id="test_robot"
        )
        self.assertEqual(res_robot["relevance_level"], "D_Irrelevant")
        
        # Representation Alignment with VLM context but demoted
        res_rep = classifier.classify(
            title="Contrastive Learning for Visual Representation Alignment in VLMs",
            abstract="We study contrastive representation alignment to map images to a shared embedding space.",
            source_id="test_rep"
        )
        self.assertEqual(res_rep["relevance_level"], "C_General_LLM_VLM_Not_PostTraining")

        # Benchmark-only without training
        res_bench = classifier.classify(
            title="A Benchmark Dataset for Chemistry QA",
            abstract="We introduce a new evaluation benchmark and dataset to measure models performance.",
            source_id="test_bench"
        )
        self.assertEqual(res_bench["relevance_level"], "C_General_LLM_VLM_Not_PostTraining")

    def test_selected_reading_queue_generation(self):
        # 7. Verify generation of selected reading queue vs full queue
        app = PostTrainRadarApp(db_path=self.db_path, overrides_path=self.overrides_path)
        
        papers = [
            {
                "title": "Core Paper",
                "venue": "ICLR",
                "year": 2025,
                "is_relevant": 1,
                "relevance_level": "A_Core_PostTraining",
                "is_core_posttraining": 1,
                "priority": "Medium",
                "reading_status": "Unread"
            },
            {
                "title": "High Priority Related Paper",
                "venue": "ICLR",
                "year": 2025,
                "is_relevant": 1,
                "relevance_level": "B_Related_LLM_VLM_Training_or_Evaluation",
                "is_core_posttraining": 0,
                "priority": "High",
                "reading_status": "Unread"
            },
            {
                "title": "Low Priority Related Paper",
                "venue": "ICLR",
                "year": 2025,
                "is_relevant": 1,
                "relevance_level": "B_Related_LLM_VLM_Training_or_Evaluation",
                "is_core_posttraining": 0,
                "priority": "Low",
                "reading_status": "Unread"
            }
        ]
        
        featured_queue = app.generate_reading_queue_featured(papers)
        full_queue = app.generate_reading_queue(papers)
        
        # Featured should include Core and High Priority Related
        self.assertIn("Core Paper", featured_queue)
        self.assertIn("High Priority Related Paper", featured_queue)
        self.assertNotIn("Low Priority Related Paper", featured_queue)
        
        # Full should include all three
        self.assertIn("Core Paper", full_queue)
        self.assertIn("High Priority Related Paper", full_queue)
        self.assertIn("Low Priority Related Paper", full_queue)

    def test_patch_scope_restriction(self):
        # 8. Verify patch scope filtering
        backflow = KnowledgeBackflow(output_dir=self.test_dir)
        
        papers = [
            {
                "title": "Core Paper",
                "venue": "ICLR",
                "year": 2025,
                "is_relevant": 1,
                "relevance_level": "A_Core_PostTraining",
                "is_core_posttraining": 1,
                "priority": "Medium",
                "model_type": "LLM",
                "post_training_types": ["DPO / Preference Optimization"],
                "keywords_matched": ["dpo"],
                "matched_evidence": {}
            },
            {
                "title": "High Priority Related",
                "venue": "ICLR",
                "year": 2025,
                "is_relevant": 1,
                "relevance_level": "B_Related_LLM_VLM_Training_or_Evaluation",
                "is_core_posttraining": 0,
                "priority": "High",
                "model_type": "LLM",
                "post_training_types": ["SFT / Instruction Tuning"],
                "keywords_matched": ["sft"],
                "matched_evidence": {}
            }
        ]
        
        # Core scope (Core only)
        res_core = backflow.run(papers, patch_scope="core")
        self.assertEqual(res_core["patches_count"], 2) # Topics: LLM, Methods: DPO
        
        # High scope (Core + High priority)
        shutil.rmtree(os.path.join(self.test_dir, "knowledge_patches"), ignore_errors=True)
        res_high_scope = backflow.run(papers, patch_scope="high")
        # High priority related adds Methods: SFT, so patch count increases
        self.assertTrue(res_high_scope["patches_count"] > 2)

    def test_dry_run_simulation(self):
        # Test dry-run behavior where files are not written to output_dir
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

    def test_siyuan_scope_filtering(self):
        app = PostTrainRadarApp(db_path=self.db_path, overrides_path=self.overrides_path)
        
        # Insert papers with different properties
        p1 = {
            "title": "Selected Paper",
            "title_norm": "selected paper",
            "abstract": "We study SFT.",
            "authors": ["Author 1"],
            "venue": "ICLR",
            "year": 2025,
            "source": "openreview",
            "source_id": "p1",
            "status": "accepted"
        }
        p1_id = app.db.insert_or_update_paper(p1)
        app.db.update_paper_tags(p1_id, {
            "is_candidate": 1,
            "is_relevant": 1,
            "relevance_level": "A_Core_PostTraining",
            "is_core_posttraining": 1,
            "include_in_siyuan": 1
        })
        
        p2 = {
            "title": "High Core Paper",
            "title_norm": "high core paper",
            "abstract": "We study RLHF.",
            "authors": ["Author 2"],
            "venue": "ICLR",
            "year": 2025,
            "source": "openreview",
            "source_id": "p2",
            "status": "accepted"
        }
        p2_id = app.db.insert_or_update_paper(p2)
        app.db.update_paper_tags(p2_id, {
            "is_candidate": 1,
            "is_relevant": 1,
            "relevance_level": "A_Core_PostTraining",
            "is_core_posttraining": 1,
            "priority": "High"
        })
        
        p3 = {
            "title": "Irrelevant Worth Sharing",
            "title_norm": "irrelevant worth sharing",
            "abstract": "Relational databases.",
            "authors": ["Author 3"],
            "venue": "ICLR",
            "year": 2025,
            "source": "openreview",
            "source_id": "p3",
            "status": "accepted"
        }
        p3_id = app.db.insert_or_update_paper(p3)
        app.db.update_paper_tags(p3_id, {
            "is_candidate": 1,
            "is_relevant": 1,
            "relevance_level": "D_Irrelevant",
            "share_status": "WorthSharing"
        })
        
        p4 = {
            "title": "Irrelevant Worth Sharing Manual Selected",
            "title_norm": "irrelevant worth sharing manual selected",
            "abstract": "Relational databases index.",
            "authors": ["Author 4"],
            "venue": "ICLR",
            "year": 2025,
            "source": "openreview",
            "source_id": "p4",
            "status": "accepted"
        }
        p4_id = app.db.insert_or_update_paper(p4)
        app.db.update_paper_tags(p4_id, {
            "is_candidate": 1,
            "is_relevant": 1,
            "relevance_level": "D_Irrelevant",
            "share_status": "WorthSharing",
            "manual_selected": 1
        })
        
        # Test selected scope
        metrics = app.run_sync(
            venue="ICLR", year=2025, target_type="siyuan",
            siyuan_scope="selected", max_siyuan_notes=0, dry_run=True
        )
        plan_synced = [p["title"] for p in metrics["plan_actually_synced"]]
        self.assertIn("Selected Paper", plan_synced)
        self.assertNotIn("High Core Paper", plan_synced)
        
        # Test high scope
        metrics_high = app.run_sync(
            venue="ICLR", year=2025, target_type="siyuan",
            siyuan_scope="high", max_siyuan_notes=0, dry_run=True
        )
        plan_synced_high = [p["title"] for p in metrics_high["plan_actually_synced"]]
        self.assertIn("Selected Paper", plan_synced_high)
        self.assertIn("High Core Paper", plan_synced_high)
        
        # Test worth_sharing scope
        metrics_ws = app.run_sync(
            venue="ICLR", year=2025, target_type="siyuan",
            siyuan_scope="worth_sharing", max_siyuan_notes=0, dry_run=True
        )
        plan_synced_ws = [p["title"] for p in metrics_ws["plan_actually_synced"]]
        self.assertIn("Selected Paper", plan_synced_ws)
        self.assertNotIn("Irrelevant Worth Sharing", plan_synced_ws)
        self.assertIn("Irrelevant Worth Sharing Manual Selected", plan_synced_ws)
        
        # Test index_only scope
        metrics_index = app.run_sync(
            venue="ICLR", year=2025, target_type="siyuan",
            siyuan_scope="index_only", max_siyuan_notes=0, dry_run=True
        )
        self.assertEqual(len(metrics_index["plan_actually_synced"]), 0)
        self.assertEqual(metrics_index["skipped_due_to_scope"], 4)

    def test_max_siyuan_notes_limit(self):
        app = PostTrainRadarApp(db_path=self.db_path, overrides_path=self.overrides_path)
        
        # Insert papers
        p1 = {
            "title": "Paper 1", "title_norm": "paper 1", "abstract": "A", "venue": "ICLR", "year": 2025, "source": "openreview", "source_id": "p1", "status": "accepted"
        }
        p1_id = app.db.insert_or_update_paper(p1)
        app.db.update_paper_tags(p1_id, {"is_candidate": 1, "is_relevant": 1, "relevance_level": "A_Core_PostTraining", "priority": "Low"})
        
        p2 = {
            "title": "Paper 2", "title_norm": "paper 2", "abstract": "B", "venue": "ICLR", "year": 2025, "source": "openreview", "source_id": "p2", "status": "accepted"
        }
        p2_id = app.db.insert_or_update_paper(p2)
        app.db.update_paper_tags(p2_id, {"is_candidate": 1, "is_relevant": 1, "relevance_level": "A_Core_PostTraining", "priority": "High"})
        
        # Sync with max limit = 1 and scope = all
        metrics = app.run_sync(
            venue="ICLR", year=2025, target_type="siyuan",
            siyuan_scope="all", max_siyuan_notes=1, dry_run=True, confirm_all_sync=True
        )
        
        self.assertEqual(len(metrics["plan_actually_synced"]), 1)
        self.assertEqual(len(metrics["plan_skipped_limit"]), 1)
        self.assertEqual(metrics["plan_actually_synced"][0]["title"], "Paper 2")
        self.assertEqual(metrics["plan_skipped_limit"][0]["title"], "Paper 1")

    def test_cleanup_siyuan_logic(self):
        from scripts.cleanup_siyuan import matches_keep_scope, has_human_content
        
        # Test matches_keep_scope logic
        p_selected = {"include_in_siyuan": 1, "relevance_level": "B_Related_LLM_VLM_Training_or_Evaluation"}
        self.assertTrue(matches_keep_scope(p_selected, "selected"))
        
        p_high_not_core = {"priority": "High", "relevance_level": "B_Related_LLM_VLM_Training_or_Evaluation"}
        self.assertFalse(matches_keep_scope(p_high_not_core, "high"))
        
        p_high_core = {"priority": "High", "relevance_level": "A_Core_PostTraining"}
        self.assertTrue(matches_keep_scope(p_high_core, "high"))
        
        # Test has_human_content detection
        boilerplate_note = """# Paper Title
## [My Reading Notes]
<!-- START_MY_READING_NOTES -->
> [!IMPORTANT]
*人工阅读记录。任何自动同步工具均绝对禁止覆盖或清空此分区。*
*   **阅读时间**: 
*   **精读笔记**: 
    *   (在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)
<!-- END_MY_READING_NOTES -->
"""
        self.assertFalse(has_human_content(boilerplate_note))
        
        user_edited_note = boilerplate_note.replace(
            "(在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)",
            "We found this paper to be extremely novel."
        )
        self.assertTrue(has_human_content(user_edited_note))

if __name__ == "__main__":
    unittest.main()
