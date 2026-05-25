import re
import json

class NoteGenerator:
    @staticmethod
    def extract_section(content: str, header_title: str, comment_start: str, comment_end: str) -> str:
        """
        Robustly extracts section content by checking HTML comment markers first,
        and falling back to Markdown headers if not found.
        """
        # 1. Try HTML comments
        pattern = re.escape(comment_start) + r"(.*?)" + re.escape(comment_end)
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 2. Try Markdown headers (e.g. ## [Section Name] or ## Section Name)
        for marker in [f"## [{header_title}]", f"## {header_title}"]:
            idx = content.find(marker)
            if idx != -1:
                start_pos = idx + len(marker)
                
                # Find next header "## " or horizontal rule "---"
                end_pos = len(content)
                next_header = content.find("\n## ", start_pos)
                next_hr = content.find("\n---", start_pos)
                
                if next_header != -1 and next_hr != -1:
                    end_pos = min(next_header, next_hr)
                elif next_header != -1:
                    end_pos = next_header
                elif next_hr != -1:
                    end_pos = next_hr
                
                return content[start_pos:end_pos].strip()
        return ""

    def generate(self, paper: dict, existing_content: str = None, overwrite: bool = False) -> str:
        """
        Generates or updates a paper reading note markdown text.
        If existing_content is provided, merges content based on V3 safety rules:
        - My Reading Notes, My Judgment, and AI Draft Review are NEVER overwritten.
        - Knowledge Backfeed Status is preserved.
        - Auto Metadata, AI Draft Summary, Knowledge Extraction, Share Decision, and Next Action
          are overwritten only if overwrite is True.
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
        
        # 1. Always regenerate Auto Metadata
        metadata_content = f"""*   **Venue**: {paper.get('venue', 'Unknown')}
*   **Year**: {paper.get('year', 2025)}
*   **Authors**: {authors_str}
*   **Source**: {paper.get('source', 'Unknown')}
*   **Status**: {paper.get('status', 'Unknown')}
*   **Data Origin**: {data_origin}
*   **Type**: #{paper.get('model_type', 'Other')}
*   **Tags**: #Unread
*   **Priority**: {paper.get('priority', 'Medium')}
*   **Relevance Level**: {paper.get('relevance_level', 'D_Irrelevant')}
*   **Core Post-Training**: {"Yes" if paper.get('is_core_posttraining') else "No"}
*   **URL**: [Abstract URL]({paper.get('paper_url') or ''})
*   **PDF**: [PDF URL]({paper.get('pdf_url') or ''})"""

        # Build Heuristic Classifier block
        kws_matched = ", ".join(paper.get("keywords_matched", []))
        matched_evidence = paper.get("matched_evidence", {})
        evidence_lines = []
        if isinstance(matched_evidence, dict):
            for section, items in matched_evidence.items():
                if isinstance(items, list):
                    lines = []
                    for item in items:
                        if isinstance(item, dict):
                            grp = item.get("keyword_group", "")
                            t_m = item.get("title_matches", [])
                            a_m = item.get("abstract_matches", [])
                            reason_text = item.get("reason_text", "")
                            
                            match_info = []
                            if t_m:
                                match_info.append(f"title: {t_m}")
                            if a_m:
                                match_info.append(f"abstract: {a_m}")
                            match_info_str = f" ({', '.join(match_info)})" if match_info else ""
                            lines.append(f"    - **{grp}**{match_info_str}: {reason_text}")
                        elif isinstance(item, str):
                            lines.append(f"    - {item}")
                    if lines:
                        evidence_lines.append(f"  - *{section}*:\n" + "\n".join(lines))
                elif isinstance(items, dict):
                    lines = []
                    for label, kws in items.items():
                        lines.append(f"    - **{label}**: {kws}")
                    if lines:
                        evidence_lines.append(f"  - *{section}*:\n" + "\n".join(lines))
        evidence_str = "\n".join(evidence_lines) if evidence_lines else "  - None"

        heuristic_block = f"""*   **Relevance**: {"Relevant" if paper.get("is_relevant") else "Not Relevant"}
*   **Confidence Score**: {paper.get("confidence", 0.0)}
*   **Reason**: {paper.get("reason", "No reason provided.")}
*   **Keywords Matched**: {kws_matched}
*   **Matched Evidence**:
{evidence_str}"""

        # 2. Extract existing content if present
        old_metadata = ""
        old_ai_draft = ""
        old_notes = ""
        old_judgment = ""
        old_review = ""
        old_extraction = ""
        old_backfeed = ""
        old_share = ""
        old_next_action = ""

        if existing_content:
            old_metadata = self.extract_section(existing_content, "Auto Metadata", "<!-- START_AUTO_METADATA -->", "<!-- END_AUTO_METADATA -->")
            old_ai_draft = self.extract_section(existing_content, "AI Draft Summary", "<!-- START_AI_DRAFT_SUMMARY -->", "<!-- END_AI_DRAFT_SUMMARY -->")
            old_notes = self.extract_section(existing_content, "My Reading Notes", "<!-- START_MY_READING_NOTES -->", "<!-- END_MY_READING_NOTES -->")
            old_judgment = self.extract_section(existing_content, "My Judgment", "<!-- START_MY_JUDGMENT -->", "<!-- END_MY_JUDGMENT -->")
            old_review = self.extract_section(existing_content, "AI Draft Review", "<!-- START_AI_DRAFT_REVIEW -->", "<!-- END_AI_DRAFT_REVIEW -->")
            old_extraction = self.extract_section(existing_content, "Knowledge Extraction", "<!-- START_KNOWLEDGE_EXTRACTION -->", "<!-- END_KNOWLEDGE_EXTRACTION -->")
            old_backfeed = self.extract_section(existing_content, "Knowledge Backfeed Status", "<!-- START_KNOWLEDGE_BACKFEED_STATUS -->", "<!-- END_KNOWLEDGE_BACKFEED_STATUS -->")
            old_share = self.extract_section(existing_content, "Share Decision", "<!-- START_SHARE_DECISION -->", "<!-- END_SHARE_DECISION -->")
            old_next_action = self.extract_section(existing_content, "Next Action", "<!-- START_NEXT_ACTION -->", "<!-- END_NEXT_ACTION -->")

        # 3. Handle Safe Sync Override logic per section

        # AI Draft Summary
        if old_ai_draft and not overwrite:
            ai_draft_content = old_ai_draft
        else:
            ai_draft_content = f"""> [!NOTE]
> *This section is auto-generated by AI.*
*   **一句话总结**: 作者认为 ______，因此提出 ______。
*   **解决的问题**: {paper.get('abstract', '')[:300]}...
*   **核心方法**: 
*   **实验结论**: 
{heuristic_block}"""

        # My Reading Notes (Protected - Never Overwritten)
        if old_notes:
            notes_content = old_notes
        else:
            notes_content = """> [!IMPORTANT]
> *人工阅读记录。任何自动同步工具均绝对禁止覆盖或清空此分区。*
*   **阅读时间**: 
*   **精读笔记**: 
    *   (在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)"""

        # My Judgment (Protected - Never Overwritten)
        if old_judgment:
            judgment_content = old_judgment
        else:
            judgment_content = """> [!IMPORTANT]
> *人工思考与批判性判断。任何自动同步工具均绝对禁止覆盖或清空此分区。*
*   **论文盲点/局限性**: 
*   **实验设计局限**: 
*   **我的评价**: 
    *   (在这里写下您对该文的真实技术评价，是否真正解决了痛点？)"""

        # AI Draft Review (Protected - Never Overwritten)
        if old_review:
            review_content = old_review
        else:
            review_content = """> [!IMPORTANT]
> *人工对 AI 生成草稿的审查记录，自动更新不会覆盖。*
*   **AI Draft 是否可信**: High / Medium / Low
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

        # Knowledge Backfeed Status (Always preserved if it exists to avoid overwriting checkboxes)
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

## [Auto Metadata]
<!-- START_AUTO_METADATA -->
{metadata_content}
<!-- END_AUTO_METADATA -->

## [AI Draft Summary]
<!-- START_AI_DRAFT_SUMMARY -->
{ai_draft_content}
<!-- END_AI_DRAFT_SUMMARY -->

## [AI Draft Review]
<!-- START_AI_DRAFT_REVIEW -->
{review_content}
<!-- END_AI_DRAFT_REVIEW -->

## [My Reading Notes]
<!-- START_MY_READING_NOTES -->
{notes_content}
<!-- END_MY_READING_NOTES -->

## [My Judgment]
<!-- START_MY_JUDGMENT -->
{judgment_content}
<!-- END_MY_JUDGMENT -->

## [Knowledge Extraction]
<!-- START_KNOWLEDGE_EXTRACTION -->
{extraction_content}
<!-- END_KNOWLEDGE_EXTRACTION -->

## [Knowledge Backfeed Status]
<!-- START_KNOWLEDGE_BACKFEED_STATUS -->
{backfeed_content}
<!-- END_KNOWLEDGE_BACKFEED_STATUS -->

## [Share Decision]
<!-- START_SHARE_DECISION -->
{share_content}
<!-- END_SHARE_DECISION -->

## [Next Action]
<!-- START_NEXT_ACTION -->
{next_action_content}
<!-- END_NEXT_ACTION -->

---
*回到主入口: [[总入口]]*"""
        return note
