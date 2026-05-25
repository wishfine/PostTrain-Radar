import re
import json

def format_tag(text: str) -> str:
    if not text:
        return ""
    # Remove spaces and non-alphanumeric/non-Chinese/non-underscore characters
    clean = text.replace(" ", "")
    clean = re.sub(r"[^\w\u4e00-\u9fa5]", "", clean)
    if not clean:
        return ""
    return f"#{clean}#"

class NoteGenerator:
    @staticmethod
    def is_top_level_header(line: str) -> bool:
        line = line.strip()
        if not line.startswith("##"):
            return False
        title = line[2:].strip()
        title = re.sub(r"^\d+\.\s*", "", title)
        title = title.strip("[]").strip()
        if "/" in title:
            title = title.split("/")[0].strip()
        
        headers = [
            "auto metadata",
            "ai draft summary",
            "classification evidence",
            "ai draft review",
            "my reading notes",
            "my judgment",
            "knowledge extraction",
            "knowledge backfeed status",
            "share decision",
            "next action",
            "my share content",
            "sources"
        ]
        return title.lower() in headers

    @staticmethod
    def extract_section(content: str, header_title: str) -> str:
        """
        Robustly extracts section content by checking Markdown headers
        supporting both ## Section Name and ## [Section Name].
        """
        if not content:
            return None
        
        lines = content.splitlines()
        header_pattern = re.compile(rf"^##\s*\[?{re.escape(header_title)}\]?\s*$")
        
        start_idx = -1
        for idx, line in enumerate(lines):
            if header_pattern.match(line.strip()):
                start_idx = idx
                break
                
        if start_idx == -1:
            return None
            
        end_idx = len(lines)
        for idx in range(start_idx + 1, len(lines)):
            stripped = lines[idx].strip()
            if stripped.startswith("---") or NoteGenerator.is_top_level_header(stripped):
                end_idx = idx
                break
                
        section_lines = lines[start_idx + 1:end_idx]
        return "\n".join(section_lines).strip()

    def generate(self, paper: dict, existing_content: str = None, overwrite: bool = False) -> str:
        """
        Generates or updates a paper reading note markdown text.
        If existing_content is provided, merges content based on heading parsing:
        - My Reading Notes, My Judgment, and AI Draft Review are NEVER overwritten.
        - Knowledge Backfeed Status is preserved.
        - Auto Metadata, AI Draft Summary, Classification Evidence, Knowledge Extraction,
          Share Decision, and Next Action are overwritten only if overwrite is True.
        
        Extremely Conservative Rule:
        If existing_content is provided but any of the protected sections are missing
        (AI Draft Review, My Reading Notes, My Judgment, Knowledge Backfeed Status),
        we print a warning and return None to skip the update.
        """
        # Standard variables from paper data
        authors = paper.get("authors", [])
        if isinstance(authors, list):
            authors_str = ", ".join(authors)
        elif isinstance(authors, str):
            try:
                parsed_authors = json.loads(authors)
                authors_str = ", ".join(parsed_authors) if isinstance(parsed_authors, list) else authors
            except Exception:
                authors_str = authors
        else:
            authors_str = "Unknown"

        post_train_str = ", ".join(paper.get("post_training_types", []))
        prob_tags_str = ", ".join(paper.get("problem_tags", []))
        data_origin = paper.get("data_origin", "openreview_api")
        
        # Format tags
        model_type_tag = format_tag(paper.get('model_type', 'Other'))
        unread_tag = format_tag('Unread')
        
        # 1. Build Auto Metadata Markdown Table
        metadata_rows = [
            f"| Venue | {paper.get('venue', 'Unknown')} |",
            f"| Year | {paper.get('year', 2025)} |",
            f"| Authors | {authors_str} |",
            f"| Source | {paper.get('source', 'Unknown')} |",
            f"| Status | {paper.get('status', 'Unknown')} |",
            f"| Data Origin | {data_origin} |",
            f"| Type | {model_type_tag} |",
            f"| Tags | {unread_tag} |",
            f"| Priority | {paper.get('priority', 'Medium')} |",
            f"| Relevance Level | {paper.get('relevance_level', 'D_Irrelevant')} |",
            f"| Core Post-Training | {'Yes' if paper.get('is_core_posttraining') else 'No'} |",
            f"| URL | [Abstract URL]({paper.get('paper_url') or ''}) |",
            f"| PDF | [PDF URL]({paper.get('pdf_url') or ''}) |"
        ]
        metadata_table = (
            "| Metadata Key | Value |\n"
            "| :--- | :--- |\n" +
            "\n".join(metadata_rows)
        )

        # Build Classification Evidence Table
        kws_matched = ", ".join(paper.get("keywords_matched", []))
        matched_evidence = paper.get("matched_evidence", {})
        evidence_rows = []
        if isinstance(matched_evidence, dict):
            for section, items in matched_evidence.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            grp = item.get("keyword_group", "")
                            t_m = ", ".join(item.get("title_matches", []))
                            a_m = ", ".join(item.get("abstract_matches", []))
                            reason_text = item.get("reason_text", "")
                            evidence_rows.append(f"| {section} | {grp} | {t_m} | {a_m} | {reason_text} |")
                        elif isinstance(item, str):
                            evidence_rows.append(f"| {section} | - | - | - | {item} |")
                elif isinstance(items, dict):
                    for label, kws in items.items():
                        evidence_rows.append(f"| {section} | {label} | - | - | {kws} |")
        
        if evidence_rows:
            classification_evidence_table = (
                "| Section | Keyword Group | Title Matches | Abstract Matches | Evidence Detail |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n" +
                "\n".join(evidence_rows)
            )
        else:
            classification_evidence_table = "*No classification evidence recorded.*"

        # 2. Extract existing content if present
        old_metadata = None
        old_ai_draft = None
        old_evidence = None
        old_review = None
        old_notes = None
        old_judgment = None
        old_extraction = None
        old_backfeed = None
        old_share = None
        old_next_action = None

        if existing_content:
            # Check for the 4 protected sections
            protected_sections = [
                "AI Draft Review",
                "My Reading Notes",
                "My Judgment",
                "Knowledge Backfeed Status"
            ]
            missing_protected = []
            for sec in protected_sections:
                extracted = self.extract_section(existing_content, sec)
                if extracted is None:
                    missing_protected.append(sec)
            
            if missing_protected:
                print(f"[!] WARNING: Skipping paper update because protected sections are missing: {missing_protected}")
                return None

            # Extract all sections
            old_metadata = self.extract_section(existing_content, "Auto Metadata")
            old_ai_draft = self.extract_section(existing_content, "AI Draft Summary")
            old_evidence = self.extract_section(existing_content, "Classification Evidence")
            old_review = self.extract_section(existing_content, "AI Draft Review")
            old_notes = self.extract_section(existing_content, "My Reading Notes")
            old_judgment = self.extract_section(existing_content, "My Judgment")
            old_extraction = self.extract_section(existing_content, "Knowledge Extraction")
            old_backfeed = self.extract_section(existing_content, "Knowledge Backfeed Status")
            old_share = self.extract_section(existing_content, "Share Decision")
            old_next_action = self.extract_section(existing_content, "Next Action")

        # 3. Handle Safe Sync Override logic per section

        # AI Draft Summary
        if old_ai_draft and not overwrite:
            ai_draft_content = old_ai_draft
        else:
            ai_draft_content = f"""*   **一句话总结**: 作者认为 ______，因此提出 ______。
*   **解决的问题**: {paper.get('abstract', '')[:300]}...
*   **核心方法**: 
*   **实验结论**: """

        # Classification Evidence
        if old_evidence and not overwrite:
            evidence_content = old_evidence
        else:
            evidence_content = f"""*   **Relevance**: {"Relevant" if paper.get("is_relevant") else "Not Relevant"}
*   **Confidence Score**: {paper.get("confidence", 0.0)}
*   **Reason**: {paper.get("reason", "No reason provided.")}
*   **Keywords Matched**: {kws_matched}

### Matched Evidence Detail
{classification_evidence_table}"""

        # My Reading Notes (Protected - Never Overwritten)
        if old_notes:
            notes_content = old_notes
        else:
            notes_content = """*   **阅读时间**: 
*   **精读笔记**: 
    *   (在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)"""

        # My Judgment (Protected - Never Overwritten)
        if old_judgment:
            judgment_content = old_judgment
        else:
            judgment_content = """*   **论文盲点/局限性**: 
*   **实验设计局限**: 
*   **我的评价**: 
    *   (在这里写下您对该文的真实技术评价，是否真正解决了痛点？)"""

        # AI Draft Review (Protected - Never Overwritten)
        if old_review:
            review_content = old_review
        else:
            review_content = """*   **AI Draft 是否可信**: High / Medium / Low
*   **错误点**: 
*   **我修正后的理解**: 
*   **是否需要重新生成**: """

        # Knowledge Extraction (Overwrite/Regenerate or Preserve)
        if old_extraction and not overwrite:
            extraction_content = old_extraction
        else:
            extraction_content = """*   **可提炼的方法/技术路线**: ➔ [[方法或机制链接]]
*   **可引入的问题意识/技术冲突**: ➔ [[问题意识链接]]
*   **有启发的后续实验设计**: """

        # Knowledge Backfeed Status (Always preserved if it exists)
        if old_backfeed:
            backfeed_content = old_backfeed
        else:
            backfeed_content = """*   [ ] 已回流 Topic 页面
*   [ ] 已回流 Method 页面
*   [ ] 已回流 Problem 页面
*   [ ] 已加入 Share 候选池
*   [ ] 已更新 阅读后思考索引"""

        # Share Decision (Overwrite/Regenerate or Preserve)
        if old_share and not overwrite:
            share_content = old_share
        else:
            share_content = """*   **是否值得分享**: 是/否
*   **分享主题建议**: 
*   **分享目标受众**: """

        # Next Action (Overwrite/Regenerate or Preserve)
        if old_next_action and not overwrite:
            next_action_content = old_next_action
        else:
            next_action_content = """*   [ ] (例如：复现代码 / 寻找对比实验基线 / 推荐给组内同学)"""

        # 4. Assemble the final template markdown
        note = f"""# {paper.get('title')}

## Auto Metadata
{metadata_table}

## AI Draft Summary
{ai_draft_content}

## Classification Evidence
{evidence_content}

## AI Draft Review
{review_content}

## My Reading Notes
{notes_content}

## My Judgment
{judgment_content}

## Knowledge Extraction
{extraction_content}

## Knowledge Backfeed Status
{backfeed_content}

## Share Decision
{share_content}

## Next Action
{next_action_content}

---
*回到主入口: [[总入口]]*"""
        return note
