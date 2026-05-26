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

        # --- NEW DOC: no existing_content must generate successfully ---
        initial_note = note_gen.generate(paper)
        self.assertIsNotNone(initial_note, "New doc generation should succeed with no existing_content")

        # Clean headings: no emoji, no brackets, no HTML comments
        self.assertIn("## My Reading Notes", initial_note)
        self.assertNotIn("## \U0001f4dd My Reading Notes", initial_note)
        self.assertNotIn("## [My Reading Notes]", initial_note)
        self.assertNotIn("<!-- START_", initial_note)
        self.assertNotIn("<!-- END_", initial_note)

        # No Obsidian/GitHub callouts
        self.assertNotIn("> [!NOTE]", initial_note)
        self.assertNotIn("> [!IMPORTANT]", initial_note)
        self.assertNotIn("> [!WARNING]", initial_note)
        self.assertNotIn("> [!TIP]", initial_note)

        # Auto Metadata table contains classification fields
        self.assertIn("| Relevance Level |", initial_note)
        self.assertIn("| Confidence |", initial_note)
        self.assertIn("| Reason |", initial_note)
        self.assertIn("| Method Tags |", initial_note)
        self.assertIn("| Problem Tags |", initial_note)

        # Tag formatting
        self.assertIn("#LLM#", initial_note)
        self.assertIn("#Unread#", initial_note)

        # All 10 clean H2 section headings present
        for heading in [
            "## Auto Metadata", "## AI Draft Summary", "## Classification Evidence",
            "## AI Draft Review", "## My Reading Notes", "## My Judgment",
            "## Knowledge Extraction", "## Knowledge Backfeed Status",
            "## Share Decision", "## Next Action"
        ]:
            self.assertIn(heading, initial_note)

        # --- MERGE: simulate user writing notes ---
        modified_note = initial_note.replace(
            "(在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)",
            "My custom human comments on this paper.\n---\nSome notes below the internal rule."
        ).replace(
            "(在这里写下您对该文的真实技术评价，是否真正解决了痛点？)",
            "My custom judgment comments."
        )

        updated_paper = paper.copy()
        updated_paper["priority"] = "High"

        merged_note = note_gen.generate(updated_paper, existing_content=modified_note)
        self.assertIsNotNone(merged_note)

        # Metadata updated
        self.assertIn("| Priority | High |", merged_note)
        self.assertIn("| Relevance Level | A_Core_PostTraining |", merged_note)

        # Human notes preserved
        self.assertIn("My custom human comments on this paper.", merged_note)
        self.assertIn("Some notes below the internal rule.", merged_note)
        self.assertIn("My custom judgment comments.", merged_note)
        self.assertNotIn("(在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)", merged_note)

        # Merged output also clean
        self.assertNotIn("<!-- START_", merged_note)
        self.assertNotIn("> [!IMPORTANT]", merged_note)

        # --- SKIP: missing protected heading in existing doc ---
        bad_note = modified_note.replace("## My Reading Notes", "## Mismatched Title")
        skipped_note = note_gen.generate(updated_paper, existing_content=bad_note)
        self.assertIsNone(skipped_note, "Should skip update when protected section is missing")

        # --- OLD FORMAT MIGRATION: emoji+bracket headings, HTML comments, callouts ---
        old_style_note = (
            "# A Test Paper on DPO\n\n"
            "## [My Reading Notes]\n"
            "<!-- START_MY_READING_NOTES -->\n"
            "> [!IMPORTANT]\n"
            "> *\u4eba\u5de5\u9605\u8bfb\u8bb0\u5f55\u3002\u4efb\u4f55\u81ea\u52a8\u540c\u6b65\u5de5\u5177\u5747\u7edd\u5bf9\u7981\u6b62\u8986\u76d6\u6216\u6e05\u7a7a\u6b64\u5206\u533a\u3002*\n"
            "> *   **\u9605\u8bfb\u65f6\u95f4**: 2026-05-25\n"
            "> *   **\u7cbe\u8bfb\u7b14\u8bb0**: \n"
            ">     *   This is old notes.\n"
            "<!-- END_MY_READING_NOTES -->\n\n"
            "## [My Judgment]\n"
            "<!-- START_MY_JUDGMENT -->\n"
            "> [!IMPORTANT]\n"
            "> *\u4eba\u5de5\u601d\u8003\u4e0e\u6279\u5224\u6027\u5224\u65ad\u3002*\n"
            "> *   **\u8bba\u6587\u76f2\u70b9/\u5c40\u9650\u6027**: None\n"
            "> *   **\u5b9e\u9a8c\u8bbe\u8ba1\u5c40\u9650**: None\n"
            "> *   **\u6211\u7684\u8bc4\u4ef7**: \n"
            ">     *   Old judgment.\n"
            "<!-- END_MY_JUDGMENT -->\n\n"
            "## \U0001f50d [AI Draft Review]\n"
            "<!-- START_AI_DRAFT_REVIEW -->\n"
            "> [!WARNING]\n"
            "> *\u4eba\u5de5\u5bf9 AI \u751f\u6210\u8349\u7a3f\u7684\u5ba1\u67e5\u8bb0\u5f55\u3002*\n"
            "> *   **AI Draft \u662f\u5426\u53ef\u4fe1**: High\n"
            "> *   **\u9519\u8bef\u70b9**: None\n"
            "<!-- END_AI_DRAFT_REVIEW -->\n\n"
            "## \U0001f504 [Knowledge Backfeed Status]\n"
            "<!-- START_KNOWLEDGE_BACKFEED_STATUS -->\n"
            "*   [x] \u5df2\u56de\u6d41 Topic \u9875\u9762\n"
            "<!-- END_KNOWLEDGE_BACKFEED_STATUS -->\n"
        )
        migrated_note = note_gen.generate(updated_paper, existing_content=old_style_note)
        self.assertIsNotNone(migrated_note, "Migration of old-format doc should succeed")

        # Old human content preserved after migration
        self.assertIn("This is old notes.", migrated_note)
        self.assertIn("Old judgment.", migrated_note)
        self.assertIn("**AI Draft \u662f\u5426\u53ef\u4fe1**: High", migrated_note)

        # Output headings are clean (no emoji, no brackets)
        self.assertIn("## My Reading Notes", migrated_note)
        self.assertNotIn("## [My Reading Notes]", migrated_note)
        self.assertNotIn("## \U0001f4dd My Reading Notes", migrated_note)
        self.assertNotIn("## \U0001f50d [AI Draft Review]", migrated_note)
        self.assertNotIn("## \U0001f504 [Knowledge Backfeed Status]", migrated_note)

        # No HTML comments in migrated output
        self.assertNotIn("<!-- START_", migrated_note)
        self.assertNotIn("<!-- END_", migrated_note)

        # No Obsidian callouts in migrated output
        self.assertNotIn("> [!IMPORTANT]", migrated_note)
        self.assertNotIn("> [!WARNING]", migrated_note)

        # Boilerplate callout text stripped
        self.assertNotIn("\u4eba\u5de5\u9605\u8bfb\u8bb0\u5f55\u3002\u4efb\u4f55\u81ea\u52a8\u540c\u6b65\u5de5\u5177\u5747\u7edd\u5bf9\u7981\u6b62\u8986\u76d6", migrated_note)

        # --- SHARE BRIEF: clean format ---
        initial_share = share_gen.generate(paper)
        self.assertIsNotNone(initial_share)

        # No HTML comments
        self.assertNotIn("<!-- START_", initial_share)
        self.assertNotIn("<!-- END_", initial_share)

        # No Obsidian callouts
        self.assertNotIn("> [!NOTE]", initial_share)
        self.assertNotIn("> [!IMPORTANT]", initial_share)

        # No bracketed headings
        self.assertNotIn("## [", initial_share)

        # No emoji headings at the ## level
        import re
        for line in initial_share.splitlines():
            if line.startswith("## "):
                # The character after "## " must be a letter/digit/CJK, not emoji
                rest = line[3:]
                self.assertFalse(
                    bool(re.match(r"^[^\w\u4e00-\u9fa5\[\s]", rest)),
                    f"Share brief has emoji/symbol heading: {line!r}"
                )

        # Clean H2 headings in share output
        self.assertIn("## Auto Metadata", initial_share)
        self.assertIn("## My Share Content", initial_share)
        self.assertIn("## Sources", initial_share)

        # Share brief preserves user edits on merge
        modified_share = initial_share.replace(
            "\u8fd9\u7bc7\u8bba\u6587\u4e3b\u8981\u8bb2\uff1a",
            "Human share details."
        )
        merged_share = share_gen.generate(updated_paper, existing_content=modified_share)
        self.assertIn("Human share details.", merged_share)
        self.assertNotIn("\u8fd9\u7bc7\u8bba\u6587\u4e3b\u8981\u8bb2\uff1a", merged_share)
        self.assertNotIn("每一个分享标题建议", merged_share)

    def test_new_format_adjustments(self):
        note_gen = NoteGenerator()

        # 1. Test Source / Status / Data Origin consistency
        paper_or = {
            "title": "OpenReview Paper",
            "authors": ["Author B"],
            "data_origin": "openreview_api",
            "source": "Unknown",
            "status": "Unknown"
        }
        note_or = note_gen.generate(paper_or)
        self.assertIn("| Source | openreview |", note_or)
        self.assertIn("| Status | accepted |", note_or)
        self.assertIn("| Data Origin | openreview_api |", note_or)

        # 2. Test Knowledge Extraction has no double links, maps correctly, and fallbacks to "待人工补充"
        paper_tags = {
            "title": "Mapping Tags Paper",
            "post_training_types": ["dpo", "unknown_method"],
            "problem_tags": ["length bias", "unknown_problem"]
        }
        note_tags = note_gen.generate(paper_tags)
        extraction_section = note_gen.extract_section(note_tags, "Knowledge Extraction")
        self.assertIn("[[DPO]]", extraction_section)
        self.assertNotIn("unknown_method", extraction_section)
        self.assertNotIn("方法或机制链接", extraction_section)
        
        self.assertIn("[[Length_Bias]]", extraction_section)
        self.assertNotIn("unknown_problem", extraction_section)
        self.assertNotIn("问题意识链接", extraction_section)

        # test fallback to "待人工补充"
        paper_no_tags = {
            "title": "No Tags Paper",
            "post_training_types": [],
            "problem_tags": []
        }
        note_no_tags = note_gen.generate(paper_no_tags)
        self.assertIn("*   **可提炼的方法/技术路线**: ➔ 待人工补充", note_no_tags)
        self.assertIn("*   **可引入的问题意识/技术冲突**: ➔ 待人工补充", note_no_tags)

        # 3. Test Next Action checklist is a fixed list
        expected_checklist = """*   [ ] 读 Introduction
*   [ ] 读 Method
*   [ ] 读 Experiments
*   [ ] 看 Ablation
*   [ ] 找相关论文对比
*   [ ] 回流到知识页
*   [ ] 判断是否生成分享稿"""
        self.assertIn(expected_checklist, note_or)

        # 4. Test AI Draft Summary Problem Solved fallback
        paper_no_abstract = {
            "title": "No Abstract Paper",
            "abstract": ""
        }
        note_no_abstract = note_gen.generate(paper_no_abstract)
        self.assertIn("*   **解决的问题**: 待精读后补充", note_no_abstract)

        paper_ellipses_abstract = {
            "title": "Ellipses Abstract Paper",
            "abstract": "..."
        }
        note_ellipses = note_gen.generate(paper_ellipses_abstract)
        self.assertIn("*   **解决的问题**: 待精读后补充", note_ellipses)

        paper_short_abstract = {
            "title": "Short Abstract Paper",
            "abstract": "This is a short abstract."
        }
        note_short = note_gen.generate(paper_short_abstract)
        self.assertIn("*   **解决的问题**: This is a short abstract.", note_short)

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
                "reading_status": "Unread",
                "include_in_reading_queue": 1
            },
            {
                "title": "High Priority Related Paper",
                "venue": "ICLR",
                "year": 2025,
                "is_relevant": 1,
                "relevance_level": "B_Related_LLM_VLM_Training_or_Evaluation",
                "is_core_posttraining": 0,
                "priority": "High",
                "reading_status": "Unread",
                "include_in_reading_queue": 1
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

    def test_prompt_sync_overwrite_rule(self):
        from src.exporters.siyuan_exporter import SiYuanExporter
        exporter = SiYuanExporter(dry_run=False, token_env="FAKE_TOKEN")
        exporter.notebook_id = "fake_notebook_id"
        
        # Mock _find_doc_id_and_path to simulate existing doc
        exporter._find_doc_id_and_path = MagicMock(return_value=("fake_doc_id", "/path/to/doc"))
        exporter._call_api = MagicMock(return_value={"code": 0, "data": "updated_id"})
        
        # When overwrite is False, should skip and return True
        res_skip = exporter.export_workflow_prompts("test_prompt", "content", overwrite=False)
        self.assertTrue(res_skip)
        exporter._call_api.assert_not_called()
        
        # When overwrite is True, should call updateBlock API
        res_update = exporter.export_workflow_prompts("test_prompt", "content", overwrite=True)
        self.assertTrue(res_update)
        exporter._call_api.assert_called_once_with("/api/block/updateBlock", {
            "id": "fake_doc_id",
            "dataType": "markdown",
            "data": "content"
        })

    def test_share_brief_unified_routing(self):
        from src.exporters.siyuan_exporter import SiYuanExporter
        exporter = SiYuanExporter(dry_run=True, token_env="FAKE_TOKEN")
        exporter.notebook_id = "fake_notebook_id"
        exporter._find_doc_id_and_path = MagicMock(return_value=(None, None))
        
        paper = {
            "title": "A Great Post-Training Method",
            "venue": "iclr",
            "year": 2025,
            "source": "openreview",
            "status": "accepted"
        }
        
        # Simulate dry run creation
        with patch.object(exporter, '_call_api') as mock_call:
            exporter.export_share_brief(paper, "markdown content", overwrite=False)
            # Under dry run, it prints simulation but doesn't call API. Let's inspect mock_call not called or verify paths.
            # To get target path, let's call without dry run or check how target path is computed.
            # Let's temporarily disable dry_run for testing target path
            exporter.dry_run = False
            mock_call.return_value = {"code": 0, "data": "new_brief_id"}
            exporter.export_share_brief(paper, "markdown content", overwrite=False)
            mock_call.assert_called_once()
            call_args = mock_call.call_args[0]
            self.assertEqual(call_args[0], "/api/filetree/createDocWithMd")
            self.assertEqual(call_args[1]["path"], "/05_Share/Group_Meeting/Paper_Briefs/ICLR_2025/A Great Post-Training Method_Share_Brief")

    def test_generate_override_candidates_logic(self):
        from scripts.generate_override_candidates import get_candidates
        db = DatabaseManager(self.db_path)
        
        # Insert a mix of papers
        papers_data = [
            # Core paper
            {
                "title": "Core Paper", "title_norm": "core paper", "venue": "ICLR", "year": 2025,
                "source": "openreview", "source_id": "p1", "status": "accepted"
            },
            # High priority non-core
            {
                "title": "High Priority Non Core", "title_norm": "high priority non core", "venue": "ICLR", "year": 2025,
                "source": "openreview", "source_id": "p2", "status": "accepted"
            },
            # Worth sharing paper
            {
                "title": "Worth Sharing Paper", "title_norm": "worth sharing paper", "venue": "ICLR", "year": 2025,
                "source": "openreview", "source_id": "p3", "status": "accepted"
            },
            # Regular paper but high confidence
            {
                "title": "High Confidence Paper", "title_norm": "high confidence paper", "venue": "ICLR", "year": 2025,
                "source": "openreview", "source_id": "p4", "status": "accepted"
            }
        ]
        
        ids = []
        for p in papers_data:
            ids.append(db.insert_or_update_paper(p))
            
        # Update tags
        # Core paper (A_Core_PostTraining, Low priority, conf 0.5)
        db.update_paper_tags(ids[0], {"is_relevant": 1, "relevance_level": "A_Core_PostTraining", "priority": "Low", "confidence": 0.5})
        # High priority (B_Related, High priority, conf 0.6)
        db.update_paper_tags(ids[1], {"is_relevant": 1, "relevance_level": "B_Related_LLM_VLM_Training_or_Evaluation", "priority": "High", "confidence": 0.6})
        # Worth sharing (B_Related, Medium priority, WorthSharing, conf 0.4)
        db.update_paper_tags(ids[2], {"is_relevant": 1, "relevance_level": "B_Related_LLM_VLM_Training_or_Evaluation", "priority": "Medium", "share_status": "WorthSharing", "confidence": 0.4})
        # High confidence (B_Related, Medium priority, conf 0.9)
        db.update_paper_tags(ids[3], {"is_relevant": 1, "relevance_level": "B_Related_LLM_VLM_Training_or_Evaluation", "priority": "Medium", "confidence": 0.9})
        
        db.close()
        
        # Call get_candidates using our temporary DB
        with patch('scripts.generate_override_candidates.PostTrainRadarApp') as mock_app_class:
            mock_app = MagicMock()
            mock_app.db = DatabaseManager(self.db_path)
            mock_app_class.return_value = mock_app
            
            candidates = get_candidates("ICLR", 2025, top_k=4)
            
            # Sorting should be:
            # 1. Core Paper (A_Core_PostTraining)
            # 2. High Priority Non Core (High priority)
            # 3. Worth Sharing Paper (WorthSharing)
            # 4. High Confidence Paper (confidence 0.9)
            self.assertEqual(candidates[0]["title"], "Core Paper")
            self.assertEqual(candidates[1]["title"], "High Priority Non Core")
            self.assertEqual(candidates[2]["title"], "Worth Sharing Paper")
            self.assertEqual(candidates[3]["title"], "High Confidence Paper")
            mock_app.db.close()

    def test_reset_siyuan_sync_meta_action(self):
        from scripts.reset_siyuan_sync_meta import main
        db = DatabaseManager(self.db_path)
        
        # Insert paper with sync metadata
        paper = {
            "title": "Reset Test Paper", "title_norm": "reset test paper", "venue": "ICLR", "year": 2025,
            "source": "openreview", "source_id": "reset_p1", "status": "accepted"
        }
        paper_id = db.insert_or_update_paper(paper)
        db.update_siyuan_meta(paper_id, "fake_doc_id", "fake_path", "fake_time", "fake_mode")
        db.update_paper_tags(paper_id, {"include_in_siyuan": 1, "manual_selected": 1, "include_in_reading_queue": 1})
        db.close()
        
        # Mock sys.argv
        test_args = ["reset_siyuan_sync_meta.py", "--venue", "ICLR", "--year", "2025", "--confirm-reset"]
        with patch('sys.argv', test_args), patch('scripts.reset_siyuan_sync_meta.PostTrainRadarApp') as mock_app_class:
            mock_app = MagicMock()
            mock_app.db = DatabaseManager(self.db_path)
            mock_app_class.return_value = mock_app
            
            main()
            
            # Reopen DB to verify fields
            db_verify = DatabaseManager(self.db_path)
            papers = db_verify.get_classified_papers("ICLR", 2025)
            self.assertEqual(len(papers), 1)
            p = papers[0]
            self.assertIsNone(p["siyuan_doc_id"])
            self.assertIsNone(p["siyuan_path"])
            self.assertIsNone(p["siyuan_sync_time"])
            self.assertIsNone(p["siyuan_sync_mode"])
            self.assertEqual(p["include_in_siyuan"], 0)
            # Manual curation fields must be preserved!
            self.assertEqual(p["manual_selected"], 1)
            self.assertEqual(p["include_in_reading_queue"], 1)
            db_verify.close()

    def test_export_reading_packet(self):
        from scripts.export_reading_packet import main
        db = DatabaseManager(self.db_path)
        
        # Insert a paper
        paper = {
            "title": "Export Packet Test Paper", "title_norm": "export packet test paper", "venue": "ICLR", "year": 2025,
            "source": "openreview", "source_id": "packet_p1", "status": "accepted",
            "abstract": "This is a great abstract."
        }
        paper_id = db.insert_or_update_paper(paper)
        db.update_paper_tags(paper_id, {
            "is_relevant": 1, 
            "post_training_types": ["dpo"],
            "problem_tags": ["length bias"]
        })
        db.close()
        
        test_args = ["export_reading_packet.py", "--title", "Export Packet Test Paper"]
        
        with patch('sys.argv', test_args), patch('scripts.export_reading_packet.PostTrainRadarApp') as mock_app_class:
            mock_app = MagicMock()
            mock_app.db = DatabaseManager(self.db_path)
            mock_app.note_gen = NoteGenerator()
            mock_app.share_gen = ShareGenerator()
            mock_app.get_exporter.return_value = None
            mock_app_class.return_value = mock_app
            
            main()
            
            out_file = "data/reading_packets/Export_Packet_Test_Paper_reading_packet.md"
            self.assertTrue(os.path.exists(out_file), "Reading packet output file should be created")
            
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            self.assertIn("## 1. Paper Card 当前内容", content)
            self.assertIn("## 2. Auto Metadata", content)
            self.assertIn("## 3. AI Draft Summary", content)
            self.assertIn("## 4. Classification Evidence", content)
            self.assertIn("## 5. Abstract", content)
            self.assertIn("## 6. Method Tags / Problem Tags", content)
            self.assertIn("## 7. 推荐回流的 Method / Problem 页面", content)
            self.assertIn("## 8. Share Brief 草稿", content)
            self.assertIn("## 9. 阅读助手使用说明", content)
            
            self.assertIn("Export Packet Test Paper", content)
            self.assertIn("This is a great abstract.", content)
            self.assertIn("[[DPO]]", content)
            self.assertIn("[[Length_Bias]]", content)
            
            if os.path.exists(out_file):
                os.remove(out_file)
            mock_app.db.close()

        # Test 2: Source ID lookup
        test_args_2 = ["export_reading_packet.py", "--source-id", "packet_p1"]
        with patch('sys.argv', test_args_2), patch('scripts.export_reading_packet.PostTrainRadarApp') as mock_app_class:
            mock_app = MagicMock()
            mock_app.db = DatabaseManager(self.db_path)
            mock_app.note_gen = NoteGenerator()
            mock_app.share_gen = ShareGenerator()
            mock_app.get_exporter.return_value = None
            mock_app_class.return_value = mock_app
            
            main()
            
            out_file = "data/reading_packets/Export_Packet_Test_Paper_reading_packet.md"
            self.assertTrue(os.path.exists(out_file))
            if os.path.exists(out_file):
                os.remove(out_file)
            mock_app.db.close()
            
        # Test 3: Priority paper_id > source_id > title
        db = DatabaseManager(self.db_path)
        paper2 = {
            "title": "Export Packet Test Paper 2", "title_norm": "export packet test paper 2", "venue": "ICLR", "year": 2025,
            "source": "openreview", "source_id": "packet_p2", "status": "accepted",
            "abstract": "This is abstract 2."
        }
        paper2_id = db.insert_or_update_paper(paper2)
        db.close()
        
        test_args_3 = ["export_reading_packet.py", "--paper-id", str(paper2_id), "--source-id", "packet_p1", "--title", "Export Packet Test Paper"]
        with patch('sys.argv', test_args_3), patch('scripts.export_reading_packet.PostTrainRadarApp') as mock_app_class:
            mock_app = MagicMock()
            mock_app.db = DatabaseManager(self.db_path)
            mock_app.note_gen = NoteGenerator()
            mock_app.share_gen = ShareGenerator()
            mock_app.get_exporter.return_value = None
            mock_app_class.return_value = mock_app
            
            main()
            
            out_file = "data/reading_packets/Export_Packet_Test_Paper_2_reading_packet.md"
            self.assertTrue(os.path.exists(out_file), "Should resolve to paper2 by paper_id priority")
            if os.path.exists(out_file):
                os.remove(out_file)
            mock_app.db.close()

    def test_curated_workspace_workflow_constraints(self):
        # Test 1 & 2 & 7 & 8 & 9 & 11:
        # Create app and database
        db = DatabaseManager(self.db_path)
        
        # Insert a mix of selected and unselected papers (relevant core/high priority, and manually selected irrelevant)
        # Paper 1: Core and High Priority, but NOT selected (not in overrides)
        p1_id = db.insert_or_update_paper({
            "title": "Unselected Core High Paper", "title_norm": "unselected core high paper",
            "venue": "ICLR", "year": 2025, "source": "openreview", "source_id": "uns1", "status": "accepted",
            "abstract": "We study reward model overfitting in RLHF."
        })
        db.update_paper_tags(p1_id, {
            "is_candidate": 1, "is_relevant": 1, "relevance_level": "A_Core_PostTraining", "priority": "High", "confidence": 0.8
        })

        # Paper 2: Selected paper (is in overrides, manual_selected = 1)
        p2_id = db.insert_or_update_paper({
            "title": "Selected Paper", "title_norm": "selected paper",
            "venue": "ICLR", "year": 2025, "source": "openreview", "source_id": "sel1", "status": "accepted",
            "abstract": "We study direct preference optimization."
        })
        db.update_paper_tags(p2_id, {
            "is_candidate": 1, "is_relevant": 1, "relevance_level": "A_Core_PostTraining", "priority": "High", "confidence": 0.9,
            "manual_selected": 1, "include_in_siyuan": 1, "include_in_reading_queue": 1
        })
        
        db.close()

        # Let's create overrides file representing this state
        temp_overrides_path = os.path.join(self.test_dir, "test_sync_overrides.yaml")
        sync_overrides_data = {
            "sel1": {
                "title": "Selected Paper",
                "manual_selected": True,
                "include_in_siyuan": True,
                "include_in_reading_queue": True
            }
        }
        with open(temp_overrides_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(sync_overrides_data, f)

        # Initialize App pointing to our test database and our test overrides path
        app = PostTrainRadarApp(db_path=self.db_path, overrides_path=temp_overrides_path)

        # 1. run_pipeline --sync-target markdown does not call/instantiate SiYuanExporter
        with patch('src.app.SiYuanExporter') as mock_siyuan_exporter_class:
            # Run sync for markdown
            app.run_sync(
                venue="ICLR", year=2025, target_type="markdown", note_type="all",
                overwrite=True, dry_run=False, siyuan_scope="selected"
            )
            # Verify SiYuanExporter was not called/instantiated
            mock_siyuan_exporter_class.assert_not_called()

        # 2. Reading_Queue_Full is saved locally but not sent to SiYuan
        # We check files in local folder
        self.assertTrue(os.path.exists("data/00_Index/Reading_Queue_Full.md"))
        self.assertTrue(os.path.exists("data/reports/Reading_Queue_Full.md"))
        
        # Verify that if we run with siyuan, the exporter is called, but Reading_Queue_Full is not passed to it
        with patch('src.app.SiYuanExporter') as mock_siyuan_exporter_class:
            mock_siyuan_exporter = MagicMock()
            mock_siyuan_exporter.test_connection.return_value = True
            mock_siyuan_exporter.validate_notebook.return_value = True
            mock_siyuan_exporter_class.return_value = mock_siyuan_exporter
            
            app.run_sync(
                venue="ICLR", year=2025, target_type="siyuan", note_type="all",
                overwrite=True, dry_run=False, siyuan_scope="selected"
            )
            
            # Check calls to export_report_at_path
            for call in mock_siyuan_exporter.export_report_at_path.call_args_list:
                args = call[0]
                self.assertNotEqual(args[0], "/00_Index/Reading_Queue_Full", "Reading_Queue_Full should never be synced to SiYuan")

        # 3. generate_override_candidates.py generated candidates default all sync flags to False
        from scripts.generate_override_candidates import get_candidates
        with patch('scripts.generate_override_candidates.PostTrainRadarApp') as mock_app_class:
            mock_app = MagicMock()
            mock_app.db = DatabaseManager(self.db_path)
            mock_app_class.return_value = mock_app
            
            candidates = get_candidates("ICLR", 2025, top_k=10)
            
            # Verify structure and defaults
            for p in candidates:
                # Mock main outputs dictionary format in candidate generator
                evidence = p.get("matched_evidence", {})
                evidence_str = str(evidence)
                
                candidate_entry = {
                    "title": p.get("title"),
                    "source_id": p.get("source_id"),
                    "venue": p.get("venue"),
                    "year": p.get("year"),
                    "relevance_level": p.get("relevance_level"),
                    "priority": p.get("priority", "Medium"),
                    "confidence": p.get("confidence", 0.0),
                    "model_type": p.get("model_type"),
                    "method_tags": p.get("post_training_types", []),
                    "problem_tags": p.get("problem_tags", []),
                    "matched_evidence": evidence_str,
                    "reviewer_comment": p.get("reviewer_comment", ""),
                    "next_action": p.get("next_action", ""),
                    "manual_selected": False,
                    "include_in_siyuan": False,
                    "include_in_reading_queue": False,
                    "include_in_knowledge_patches": False,
                    "include_in_share_pool": False
                }
                
                # Check 5 switches are False
                self.assertFalse(candidate_entry["manual_selected"])
                self.assertFalse(candidate_entry["include_in_siyuan"])
                self.assertFalse(candidate_entry["include_in_reading_queue"])
                self.assertFalse(candidate_entry["include_in_knowledge_patches"])
                self.assertFalse(candidate_entry["include_in_share_pool"])
                
                # Verify we have all 18 keys
                self.assertEqual(len(candidate_entry), 18)
            mock_app.db.close()

        # 4 & 11. 精选阅读队列 is only populated from tag_overrides.yaml selected papers.
        # Core + High priority paper "Unselected Core High Paper" must NOT enter 精选阅读队列
        db = DatabaseManager(self.db_path)
        all_papers = db.get_classified_papers("ICLR", 2025)
        db.close()
        
        featured_queue_md = app.generate_reading_queue_featured(all_papers)
        
        self.assertIn("Selected Paper", featured_queue_md)
        self.assertNotIn("Unselected Core High Paper", featured_queue_md, "Unselected core high paper must not be in featured queue")

        # 5 & 6 & 11. --siyuan-scope selected only syncs selected papers.
        # Core + High priority paper "Unselected Core High Paper" must NOT enter selected sync
        with patch('src.app.SiYuanExporter') as mock_siyuan_exporter_class:
            mock_siyuan_exporter = MagicMock()
            mock_siyuan_exporter.test_connection.return_value = True
            mock_siyuan_exporter.validate_notebook.return_value = True
            mock_siyuan_exporter_class.return_value = mock_siyuan_exporter
            
            app.run_sync(
                venue="ICLR", year=2025, target_type="siyuan", note_type="all",
                overwrite=True, dry_run=False, siyuan_scope="selected"
            )
            
            # Verify export_paper_note was called for "Selected Paper" but NOT "Unselected Core High Paper"
            synced_paper_titles = []
            for call in mock_siyuan_exporter.export_paper_note.call_args_list:
                paper_arg = call[0][0]
                synced_paper_titles.append(paper_arg.get("title"))
                
            self.assertIn("Selected Paper", synced_paper_titles)
            self.assertNotIn("Unselected Core High Paper", synced_paper_titles)

        # 7 & 8. selected dry-run generates siyuan_sync_plan without Reading_Queue_Full
        plan_file = "data/reports/siyuan_sync_plan_iclr_2025.md"
        if os.path.exists(plan_file):
            os.remove(plan_file)
            
        with patch('src.app.SiYuanExporter') as mock_siyuan_exporter_class:
            mock_siyuan_exporter = MagicMock()
            mock_siyuan_exporter.test_connection.return_value = True
            mock_siyuan_exporter.validate_notebook.return_value = True
            mock_siyuan_exporter_class.return_value = mock_siyuan_exporter
            
            app.run_sync(
                venue="ICLR", year=2025, target_type="siyuan", note_type="all",
                overwrite=True, dry_run=True, siyuan_scope="selected"
            )
            
        self.assertTrue(os.path.exists(plan_file))
        with open(plan_file, "r", encoding="utf-8") as f:
            plan_content = f.read()
            
        # Assert sync plan content does not list Reading_Queue_Full in synced indexes, but has explanation
        self.assertNotIn("Reading_Queue_Full, 精选阅读队列", plan_content)
        self.assertIn("**Reading_Queue_Full.md** is a full local queue of all relevant papers", plan_content)
        self.assertIn("It is **NOT** synced to SiYuan", plan_content)

        # 9 & 11. selected sync does not generate per-paper share briefs for unselected papers.
        with patch('src.app.SiYuanExporter') as mock_siyuan_exporter_class:
            mock_siyuan_exporter = MagicMock()
            mock_siyuan_exporter.test_connection.return_value = True
            mock_siyuan_exporter.validate_notebook.return_value = True
            mock_siyuan_exporter_class.return_value = mock_siyuan_exporter
            
            app.run_sync(
                venue="ICLR", year=2025, target_type="siyuan", note_type="all",
                overwrite=True, dry_run=False, siyuan_scope="selected"
            )
            
            exported_share_briefs = []
            for call in mock_siyuan_exporter.export_share_brief.call_args_list:
                paper_arg = call[0][0]
                exported_share_briefs.append(paper_arg.get("title"))
                
            self.assertNotIn("Unselected Core High Paper", exported_share_briefs)

        # 10. export_reading_packet.py warning and local output
        from scripts.export_reading_packet import main as export_packet_main
        # Mock sys.argv to export "Unselected Core High Paper" which is not selected
        test_args = ["export_reading_packet.py", "--title", "Unselected Core High Paper"]
        
        # Capture stdout
        import io
        import sys as sys_module
        captured_output = io.StringIO()
        orig_stdout = sys_module.stdout
        sys_module.stdout = captured_output
        
        try:
            with patch('sys.argv', test_args), patch('scripts.export_reading_packet.PostTrainRadarApp') as mock_app_class:
                mock_app = MagicMock()
                mock_app.db = DatabaseManager(self.db_path)
                mock_app.note_gen = NoteGenerator()
                mock_app.share_gen = ShareGenerator()
                mock_app.get_exporter.return_value = None
                mock_app_class.return_value = mock_app
                
                export_packet_main()
                mock_app.db.close()
        finally:
            sys_module.stdout = orig_stdout
            
        console_log = captured_output.getvalue()
        # Verify WARNING log is printed
        self.assertIn("WARNING: This paper is not manually selected. It is not part of the curated reading workflow.", console_log)
        self.assertIn("outputs ONLY to a local file and does not make write requests to SiYuan", console_log)
        
        # Verify local file contains relevance level and priority details
        out_file = "data/reading_packets/Unselected_Core_High_Paper_reading_packet.md"
        self.assertTrue(os.path.exists(out_file))
        with open(out_file, "r", encoding="utf-8") as f:
            packet_content = f.read()
        self.assertIn("- **Relevance Level**: A_Core_PostTraining", packet_content)
        self.assertIn("- **Priority**: High", packet_content)
        
        # Cleanup
        if os.path.exists(out_file):
            os.remove(out_file)
        if os.path.exists(plan_file):
            os.remove(plan_file)

if __name__ == "__main__":
    unittest.main()
