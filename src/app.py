import os
import yaml
import json
import logging
from datetime import datetime
from src.database import DatabaseManager
from src.normalizer import normalize_title, compute_abstract_hash
from src.deduplicator import Deduplicator
from src.keyword_filter import KeywordFilter
from src.classifier import RuleClassifier
from src.reporter import ReportGenerator
from src.note_generator import NoteGenerator
from src.share_generator import ShareGenerator
from src.knowledge_backflow import KnowledgeBackflow

from src.collectors.openreview_collector import OpenReviewCollector
from src.collectors.acl_collector import ACLCollector
from src.collectors.cvf_collector import CVFCollector

from src.exporters.markdown_exporter import MarkdownExporter, safe_filename
from src.exporters.siyuan_exporter import SiYuanExporter
from src.exporters.obsidian_exporter import ObsidianExporter
from src.exporters.notion_exporter import NotionExporter
from src.exporters.zotero_exporter import ZoteroExporter

logger = logging.getLogger("PostTrainRadar")

class PostTrainRadarApp:
    def __init__(self, db_path="data/posttrain_radar.db", overrides_path="data/manual/tag_overrides.yaml"):
        self.db_path = db_path
        self.overrides_path = overrides_path
        self.db = DatabaseManager(self.db_path)
        self.dedup = Deduplicator(threshold=95.0)
        self.filter = KeywordFilter("config/keywords.yaml")
        self.classifier = RuleClassifier("config/categories.yaml", self.overrides_path)
        self.note_gen = NoteGenerator()
        self.share_gen = ShareGenerator()

    def get_collector(self, source_type: str):
        if source_type == "openreview":
            return OpenReviewCollector()
        elif source_type == "acl":
            return ACLCollector()
        elif source_type == "cvf":
            return CVFCollector()
        else:
            raise ValueError(f"Unknown collector source: {source_type}")

    def get_exporter(self, target_type: str, dry_run: bool = False) -> list:
        # Load config
        with open("config/note_targets.yaml", "r", encoding="utf-8") as f:
            targets_cfg = yaml.safe_load(f)

        if target_type == "markdown":
            cfg = targets_cfg.get("markdown", {})
            return MarkdownExporter(output_dir=cfg.get("output_dir", "data"), dry_run=dry_run)
        elif target_type == "obsidian":
            cfg = targets_cfg.get("obsidian", {})
            return ObsidianExporter(
                vault_path=cfg.get("vault_path", ""), 
                root_dir=cfg.get("root_dir", "PostTrain Radar"),
                dry_run=dry_run
            )
        elif target_type == "siyuan":
            cfg = targets_cfg.get("siyuan", {})
            return SiYuanExporter(
                api_url=cfg.get("api_url", "http://127.0.0.1:6806"),
                token_env=cfg.get("token_env", "SIYUAN_TOKEN"),
                notebook_name=cfg.get("notebook_name", "PostTrain Radar"),
                notebook_id=cfg.get("notebook_id", ""),
                dry_run=dry_run
            )
        elif target_type == "notion":
            return NotionExporter()
        elif target_type == "zotero":
            return ZoteroExporter()
        else:
            raise ValueError(f"Unknown exporter target: {target_type}")

    def run_collect(self, venue: str, year: int, source_type: str = "openreview") -> list:
        collector = self.get_collector(source_type)
        raw_papers = collector.collect(venue, year)
        
        # Load existing papers from DB to perform deduplication
        existing_papers = self.db.get_classified_papers()

        saved_ids = []
        for p in raw_papers:
            # Normalize title & compute hash
            p["title_norm"] = normalize_title(p["title"])
            p["abstract_hash"] = compute_abstract_hash(p.get("abstract", ""))
            p["venue"] = venue
            p["year"] = year
            # data_origin is set by collector (defaults to openreview_api)
            if "data_origin" not in p:
                p["data_origin"] = "openreview_api"

            # Check overrides to see if data_origin is overridden
            title_norm = p["title_norm"]
            source_id = p.get("source_id")
            
            # Check by source_id or title_norm in overrides
            override = None
            if source_id and str(source_id).lower().strip() in self.classifier.overrides:
                override = self.classifier.overrides[str(source_id).lower().strip()]
            elif title_norm in self.classifier.overrides:
                override = self.classifier.overrides[title_norm]
            
            if override and "data_origin" in override:
                p["data_origin"] = override["data_origin"]

            # Deduplicate
            dup = self.dedup.find_duplicate(p, existing_papers)
            if dup:
                logger.info(f"[*] Paper already exists (Duplicate detected): {p['title']}. Updating existing record.")
                p["source_id"] = dup["source_id"]
                p_id = self.db.insert_or_update_paper(p)
            else:
                p_id = self.db.insert_or_update_paper(p)
            
            saved_ids.append(p_id)
        
        return saved_ids

    def run_filter(self, paper_ids: list = None) -> int:
        papers = self.db.get_classified_papers()
        candidate_count = 0

        for p in papers:
            if paper_ids and p["id"] not in paper_ids:
                continue

            res = self.filter.check_paper(p["title"], p["abstract"])
            
            tag_data = {
                "is_candidate": 1 if res["is_candidate"] else 0,
                "keywords_matched": res["keywords_matched"],
                "reason": res["candidate_reason"]
            }
            
            # Check if override forces is_candidate
            title_norm = p.get("title_norm")
            source_id = p.get("source_id")
            override = None
            if source_id and str(source_id).lower().strip() in self.classifier.overrides:
                override = self.classifier.overrides[str(source_id).lower().strip()]
            elif title_norm in self.classifier.overrides:
                override = self.classifier.overrides[title_norm]

            if override and "is_candidate" in override:
                tag_data["is_candidate"] = 1 if override["is_candidate"] else 0

            self.db.update_paper_tags(p["id"], tag_data)

            if tag_data["is_candidate"]:
                candidate_count += 1

        return candidate_count

    def run_classify(self, paper_ids: list = None) -> int:
        papers = self.db.get_classified_papers()
        relevant_count = 0

        for p in papers:
            if paper_ids and p["id"] not in paper_ids:
                continue
            
            # Only classify if is_candidate is true
            if not p.get("is_candidate"):
                self.db.update_paper_tags(p["id"], {"is_relevant": 0})
                continue

            res = self.classifier.classify(p["title"], p["abstract"], p["source_id"])
            self.db.update_paper_tags(p["id"], res)

            if res["is_relevant"]:
                relevant_count += 1

        return relevant_count

    def generate_reading_queue(self, papers: list) -> str:
        """
        Formats classified papers into a Reading Queue document.
        """
        relevant_papers = [p for p in papers if p.get("is_relevant") and p.get("reading_status", "Unread") in ["Unread", "Reading"]]
        
        high_prio = []
        med_prio = []
        low_prio = []

        for p in relevant_papers:
            prio = p.get("priority", "Medium")
            if prio == "High":
                high_prio.append(p)
            elif prio == "Medium":
                med_prio.append(p)
            else:
                low_prio.append(p)

        def make_table(paper_list):
            if not paper_list:
                return "*（暂无此类论文）*\n"
            lines = [
                "| 论文名称 | 会议 | 模型类型 | 后训练方向 | 阅读状态 | 分享状态 | 下一步行动 |",
                "| :--- | :--- | :--- | :--- | :---: | :---: | :--- |"
            ]
            for p in paper_list:
                methods = ", ".join(p.get("post_training_types", []))
                lines.append(
                    f"| [[{p.get('title')}]] | {p.get('venue')} {p.get('year')} | "
                    f"{p.get('model_type')} | {methods} | {p.get('reading_status', 'Unread')} | "
                    f"{p.get('share_status', 'Not Started')} | {p.get('next_action') or 'N/A'} |"
                )
            return "\n".join(lines) + "\n"

        queue_md = f"""# 待读论文队列

本页面由 PostTrain Radar 自动维护，按优先级展示未读/正在阅读的论文。你可以在笔记软件中或者在 `data/manual/tag_overrides.yaml` 中更新其阅读状态、分享状态与下一步计划。

## 🔴 高优先级 (High Priority)
{make_table(high_prio)}

## 🟡 中优先级 (Medium Priority)
{make_table(med_prio)}

## 🟢 低优先级 (Low Priority)
{make_table(low_prio)}
"""
        return queue_md

    def generate_reading_thoughts(self, papers: list) -> str:
        """
        Formats read papers into a Reading Thoughts Index.
        """
        read_papers = [p for p in papers if p.get("is_relevant") and p.get("reading_status") == "Read"]
        
        # Fallback: if no papers are marked Read, check if they are being read or have user ratings/comments
        if not read_papers:
            read_papers = [p for p in papers if p.get("is_relevant") and (p.get("my_rating") or p.get("next_action") or p.get("reading_status") == "Reading")]

        lines = [
            "# 阅读后思考索引",
            "",
            "本页面记录已读或精读论文的核心判断、个人理解与后续沉淀观点。",
            "",
            "| 论文名称 | 会议 | 阅读状态 | 个人评分 | 下一步行动 / 沉淀观点 |",
            "| :--- | :--- | :---: | :---: | :--- |"
        ]

        if not read_papers:
            lines.append("| *（暂无已读论文记录）* | | | | |")
        else:
            for p in read_papers:
                title = p.get("title", "")
                venue = p.get("venue", "")
                year = p.get("year", 2025)
                status = p.get("reading_status", "Read")
                rating = p.get("my_rating") or "-"
                next_action = p.get("next_action") or "无"
                lines.append(f"| [[{title}]] | {venue} {year} | {status} | {rating} | {next_action} |")

        return "\n".join(lines) + "\n"

    def generate_share_pool(self, papers: list) -> str:
        """
        Formats papers suitable for sharing into a candidate pool.
        """
        share_papers = [
            p for p in papers 
            if p.get("is_relevant") and (
                p.get("confidence", 0.0) >= 0.65 or 
                p.get("priority") in ["High", "Medium"] or 
                p.get("share_status") in ["Candidate", "To Share", "Shared"]
            )
        ]

        lines = [
            "# Group_Meeting 分享候选池",
            "",
            "本页面展示适合组会分享的论文候选及已生成的分享稿链接。",
            "",
            "| 论文名称 | 会议 | 后训练方向 | 推荐度 / 置信度 | 分享状态 | 分享稿链接 |",
            "| :--- | :--- | :--- | :---: | :---: | :--- |"
        ]

        if not share_papers:
            lines.append("| *（暂无分享候选）* | | | | | |")
        else:
            for p in share_papers:
                title = p.get("title", "")
                venue = p.get("venue", "")
                year = p.get("year", 2025)
                methods = ", ".join(p.get("post_training_types", []))
                conf = p.get("confidence", 0.0)
                status = p.get("share_status", "Not Started")
                share_brief_link = f"[[{title}_Share_Brief]]"
                lines.append(f"| [[{title}]] | {venue} {year} | {methods} | {conf:.2f} | {status} | {share_brief_link} |")

        return "\n".join(lines) + "\n"

    def generate_reading_queue_featured(self, papers: list) -> str:
        """
        Formats featured papers into a Reading Queue document.
        Featured criteria: A_Core_PostTraining OR High priority OR manual override (include_in_reading_queue == 1) OR share_status == 'WorthSharing'.
        Only shows papers with reading_status in ['Unread', 'Reading'].
        """
        featured_papers = []
        for p in papers:
            if not p.get("is_relevant"):
                continue
            status = p.get("reading_status", "Unread")
            if status not in ["Unread", "Reading"]:
                continue
            
            is_a_core = (p.get("relevance_level") == "A_Core_PostTraining" or p.get("is_core_posttraining") == 1)
            is_high_prio = (p.get("priority") == "High")
            is_manual_selected = (p.get("include_in_reading_queue") == 1)
            is_worth_sharing = (p.get("share_status") == "WorthSharing" or (p.get("share_status") and "WorthSharing" in p.get("share_status")))
            
            if is_a_core or is_high_prio or is_manual_selected or is_worth_sharing:
                featured_papers.append(p)
                
        high_prio = []
        med_prio = []
        low_prio = []

        for p in featured_papers:
            prio = p.get("priority", "Medium")
            if prio == "High":
                high_prio.append(p)
            elif prio == "Medium":
                med_prio.append(p)
            else:
                low_prio.append(p)

        def make_table(paper_list):
            if not paper_list:
                return "*（暂无此类论文）*\n"
            lines = [
                "| 论文名称 | 会议 | 模型类型 | 后训练方向 | 阅读状态 | 分享状态 | 下一步行动 |",
                "| :--- | :--- | :--- | :--- | :---: | :---: | :--- |"
            ]
            for p in paper_list:
                methods = ", ".join(p.get("post_training_types", []))
                lines.append(
                    f"| [[{p.get('title')}]] | {p.get('venue')} {p.get('year')} | "
                    f"{p.get('model_type')} | {methods} | {p.get('reading_status', 'Unread')} | "
                    f"{p.get('share_status', 'Not Started')} | {p.get('next_action') or 'N/A'} |"
                )
            return "\n".join(lines) + "\n"

        queue_md = f"""# 精选阅读队列
        
本页面由 PostTrain Radar 自动维护，按优先级展示精选后训练论文（包含 Core 级、高优先级或人工指定的优质论文）。你可以在笔记软件中或者在 `data/manual/tag_overrides.yaml` 中更新其阅读状态、分享状态与下一步计划。

## 🔴 高优先级 (High Priority)
{make_table(high_prio)}

## 🟡 中优先级 (Medium Priority)
{make_table(med_prio)}

## 🟢 低优先级 (Low Priority)
{make_table(low_prio)}
"""
        return queue_md

    def run_sync(self, venue: str, year: int, target_type: str, note_type: str = "all", overwrite: bool = False, dry_run: bool = False, patch_scope: str = "high") -> dict:
        exporter = self.get_exporter(target_type, dry_run=dry_run)
        
        metrics = {
            "sync_count": 0,
            "skipped_count": 0,
            "failed_count": 0
        }

        if not exporter.test_connection():
            logger.error(f"[!] Target exporter '{target_type}' connection test failed. Sync aborted.")
            return metrics

        papers = self.db.get_classified_papers(venue, year)
        relevant_papers = [p for p in papers if p.get("is_relevant")]

        # 1. Sync Report
        if note_type in ["report", "all"]:
            report_gen = ReportGenerator(venue, year)
            report_md = report_gen.generate(papers)
            report_name = f"{venue}_{year}_Report"
            success = exporter.export_report(report_name, report_md, overwrite=overwrite)
            if success:
                metrics["sync_count"] += 1
            else:
                metrics["failed_count"] += 1

        # 2. Sync Reading Notes and Share Briefs
        for p in relevant_papers:
            if note_type in ["reading_notes", "all"]:
                note_md = self.note_gen.generate(p, overwrite=overwrite)
                success = exporter.export_paper_note(p, note_md, overwrite=overwrite)
                if success:
                    # Check if exporter returned a siyuan_doc_id
                    if not dry_run and target_type == "siyuan" and "siyuan_doc_id" in p:
                        sync_time = datetime.now().isoformat()
                        sync_mode = "overwrite" if overwrite else "merge"
                        self.db.update_siyuan_meta(
                            p["id"], 
                            p["siyuan_doc_id"], 
                            p["siyuan_path"], 
                            sync_time=sync_time, 
                            sync_mode=sync_mode
                        )
                    metrics["sync_count"] += 1
                else:
                    metrics["failed_count"] += 1

            if note_type in ["share_briefs", "all"]:
                # Generates for High & Medium priority (confidence >= 0.65)
                if p.get("confidence", 0.0) >= 0.65 or p.get("priority") in ["High", "Medium"]:
                    share_md = self.share_gen.generate(p)
                    success = exporter.export_share_brief(p, share_md, overwrite=overwrite)
                    if success:
                        metrics["sync_count"] += 1
                    else:
                        metrics["failed_count"] += 1

        # 3. Sync Reading Queue and Suggestions Index
        if note_type in ["all"]:
            # Generate Reading Queue (Full)
            queue_md = self.generate_reading_queue(papers)
            success = exporter.export_report_at_path("/00_Index/Reading_Queue_Full", queue_md, overwrite=True)
            if success:
                metrics["sync_count"] += 1

            # Generate Reading Queue (Featured)
            queue_featured_md = self.generate_reading_queue_featured(papers)
            success_featured = exporter.export_report_at_path("/00_Index/精选阅读队列", queue_featured_md, overwrite=True)
            if success_featured:
                metrics["sync_count"] += 1

            # Generate Reading Thoughts Index
            thoughts_md = self.generate_reading_thoughts(papers)
            success_thoughts = exporter.export_report_at_path("/00_Index/阅读后思考索引", thoughts_md, overwrite=True)
            if success_thoughts:
                metrics["sync_count"] += 1

            # Generate Group_Meeting Share Candidate Pool
            share_pool_md = self.generate_share_pool(papers)
            success_share_pool = exporter.export_report_at_path("/05_Share/Group_Meeting 分享候选池", share_pool_md, overwrite=True)
            if success_share_pool:
                metrics["sync_count"] += 1

            # Generate suggestions
            backflow = KnowledgeBackflow("data")
            backflow_res = backflow.run(papers, patch_scope=patch_scope)
            
            # Read compiled suggestions md
            sug_path = backflow_res["suggestions_path"]
            if os.path.exists(sug_path):
                with open(sug_path, "r", encoding="utf-8") as f:
                    sug_md = f.read()
                success_sug = exporter.export_report_at_path("/00_Index/知识回流建议", sug_md, overwrite=True)
                if success_sug:
                    metrics["sync_count"] += 1

            # Sync Prompts
            self.sync_workflow_prompts(exporter, overwrite)

        return metrics

    def sync_workflow_prompts(self, exporter, overwrite: bool = False):
        prompts_dir = "config/prompts"
        if not os.path.exists(prompts_dir):
            return
        
        for fn in os.listdir(prompts_dir):
            if fn.endswith(".md"):
                prompt_name = fn[:-3]
                path = os.path.join(prompts_dir, fn)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                exporter.export_workflow_prompts(prompt_name, content, overwrite)

    def run_pipeline(self, venue: str, year: int, source_type: str = "openreview", target_exporter: str = "markdown", overwrite: bool = False, dry_run: bool = False, patch_scope: str = "high"):
        """
        Executes the entire end-to-end flow.
        """
        # Set up logging dynamically
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/pipeline_{venue}_{year}_{timestamp}.log"
        
        logger.handlers.clear()
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(log_filename, encoding="utf-8")
        ch = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)

        logger.info(f"=== Starting PostTrain Radar Pipeline (v0.1.1) for {venue} {year} ===")
        if dry_run:
            logger.info("[!] DRY RUN ENABLED - No writes will be committed.")

        # 1. Collect
        saved_ids = self.run_collect(venue, year, source_type)
        total_count = len(saved_ids)
        logger.info(f"[1/4] Collection completed. Standardized papers: {total_count}")

        # 2. Filter
        candidate_count = self.run_filter(saved_ids)
        logger.info(f"[2/4] Keyword screening completed. Candidates: {candidate_count}")

        # 3. Classify
        relevant_count = self.run_classify(saved_ids)
        logger.info(f"[3/4] Taxonomy classification completed. Relevant papers: {relevant_count}")

        # 4. Sync
        logger.info(f"[4/4] Syncing metadata & notes (Target: {target_exporter}, Overwrite: {overwrite})...")
        sync_metrics = self.run_sync(venue, year, target_exporter, note_type="all", overwrite=overwrite, dry_run=dry_run, patch_scope=patch_scope)

        # 5. Write consolidated Run Summary Report
        # Re-fetch updated papers from database to count relevance levels and priorities correctly
        papers_db = self.db.get_classified_papers(venue, year)
        fallback_enabled = any(p.get("data_origin") == "fallback_fixture" for p in papers_db)
        
        api_count = sum(1 for p in papers_db if p.get("data_origin") == "openreview_api")
        fallback_count = sum(1 for p in papers_db if p.get("data_origin") == "fallback_fixture")
        manual_count = sum(1 for p in papers_db if p.get("data_origin") == "manual_import")

        core_count = sum(1 for p in papers_db if p.get("relevance_level") == "A_Core_PostTraining" or p.get("is_core_posttraining") == 1)
        level_breakdown = {
            "A_Core_PostTraining": sum(1 for p in papers_db if p.get("relevance_level") == "A_Core_PostTraining"),
            "B_Related_LLM_VLM_Training_or_Evaluation": sum(1 for p in papers_db if p.get("relevance_level") == "B_Related_LLM_VLM_Training_or_Evaluation"),
            "C_General_LLM_VLM_Not_PostTraining": sum(1 for p in papers_db if p.get("relevance_level") == "C_General_LLM_VLM_Not_PostTraining"),
            "D_Irrelevant": sum(1 for p in papers_db if p.get("relevance_level") == "D_Irrelevant")
        }
        high_prio_count = sum(1 for p in papers_db if p.get("priority") == "High")
        
        selected_reading_count = 0
        for p in papers_db:
            if not p.get("is_relevant"):
                continue
            status = p.get("reading_status", "Unread")
            if status not in ["Unread", "Reading"]:
                continue
            is_a_core = (p.get("relevance_level") == "A_Core_PostTraining" or p.get("is_core_posttraining") == 1)
            is_high = (p.get("priority") == "High")
            is_manual = (p.get("include_in_reading_queue") == 1)
            is_worth = (p.get("share_status") == "WorthSharing" or (p.get("share_status") and "WorthSharing" in p.get("share_status")))
            if is_a_core or is_high or is_manual or is_worth:
                selected_reading_count += 1

        summary_md = f"""# PostTrain Radar Run Summary: {venue} {year}

- **Timestamp**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Dry Run**: {"Enabled" if dry_run else "Disabled"}
- **Source Scraper**: {source_type}
- **Data Origin Breakdown**:
  - `openreview_api` (API live query): {api_count}
  - `fallback_fixture` (Fixture data): {fallback_count}
  - `manual_import` (Manual logs): {manual_count}

## Operations Metrics
- **Total Standardized**: {total_count}
- **Fallback Fixtures Triggered**: {"Yes" if fallback_enabled else "No"}
- **Keywords Candidates Screened**: {candidate_count}
- **Taxonomy Relevant Papers Identified**: {relevant_count}
- **Core Post-Training Papers Identified**: {core_count}
- **Relevance Level Breakdown**:
  - `A_Core_PostTraining`: {level_breakdown["A_Core_PostTraining"]}
  - `B_Related_LLM_VLM_Training_or_Evaluation`: {level_breakdown["B_Related_LLM_VLM_Training_or_Evaluation"]}
  - `C_General_LLM_VLM_Not_PostTraining`: {level_breakdown["C_General_LLM_VLM_Not_PostTraining"]}
  - `D_Irrelevant`: {level_breakdown["D_Irrelevant"]}
- **High Priority Count**: {high_prio_count}
- **Selected Reading Queue Count**: {selected_reading_count}

## Notes Sync Metrics (Target: {target_exporter})
- **Synced / Exported Documents**: {sync_metrics["sync_count"]}
- **Skipped Documents**: {sync_metrics["skipped_count"]}
- **Failed Transfers**: {sync_metrics["failed_count"]}
"""
        summary_dir = "data/reports"
        os.makedirs(summary_dir, exist_ok=True)
        summary_path = os.path.join(summary_dir, f"run_summary_{venue.lower()}_{year}.md")
        
        if not dry_run:
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary_md)
            logger.info(f"[+] Run summary saved to {summary_path}")
        else:
            logger.info(f"[*] [DRY-RUN] Would save run summary to: {summary_path}")

        # Record Run stats in runs table
        if not dry_run:
            self.db.insert_run({
                "source": source_type,
                "venue": venue,
                "year": year,
                "total_count": total_count,
                "candidate_count": candidate_count,
                "relevant_count": relevant_count
            })

        logger.info("=== Pipeline Execution Finished Successfully ===\n")
        return True
