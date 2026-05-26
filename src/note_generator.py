import re
import json

def normalize_heading(title_str: str) -> str:
    # Strip brackets, emojis, and punctuation, leaving letters, numbers, spaces, and Chinese characters
    t = title_str.strip("[]").strip()
    t = re.sub(r"[^\w\s\u4e00-\u9fa5]", "", t).strip()
    return t.lower()

def format_tag(text: str) -> str:
    if not text:
        return ""
    clean = text.replace(" ", "")
    clean = re.sub(r"[^\w\u4e00-\u9fa5]", "", clean)
    if not clean:
        return ""
    return f"#{clean}#"

def format_tags_list(tags) -> str:
    if not tags:
        return ""
    if isinstance(tags, str):
        try:
            parsed = json.loads(tags)
            if isinstance(parsed, list):
                tags = parsed
            else:
                tags = [tags]
        except Exception:
            tags = [t.strip() for t in tags.split(",") if t.strip()]
    
    formatted = []
    for tag in tags:
        # Split on '/' or ',' if present, e.g. "DPO / Preference Optimization"
        parts = re.split(r"[/,]", tag)
        for part in parts:
            clean = part.replace(" ", "")
            clean = re.sub(r"[^\w\u4e00-\u9fa5]", "", clean)
            if clean:
                formatted.append(f"#{clean}#")
    return " ".join(formatted)

KNOWN_METHODS = {
    "sft": "SFT",
    "rlhf": "RLHF",
    "dpo": "DPO",
    "grpo": "GRPO",
    "reward modeling": "Reward_Modeling",
    "reward model": "Reward_Modeling",
    "process reward model": "Process_Reward_Model",
    "prm": "Process_Reward_Model",
    "verifier": "Verifier_Critic",
    "critic": "Verifier_Critic",
    "test time scaling": "Test_Time_Scaling",
    "test-time scaling": "Test_Time_Scaling",
    "multimodal alignment": "Multimodal_Alignment",
    "multimodal": "Multimodal_Alignment"
}

KNOWN_PROBLEMS = {
    "reward hacking": "Reward_Hacking",
    "length bias": "Length_Bias",
    "credit assignment": "Credit_Assignment",
    "distribution shift": "Distribution_Shift",
    "reward model overfitting": "Reward_Model_Overfitting",
    "evaluation leakage": "Evaluation_Leakage",
    "multimodal hallucination": "Multimodal_Hallucination",
    "visual grounding failure": "Visual_Grounding_Failure",
    "tool use credit assignment": "Tool_Use_Credit_Assignment",
    "test time compute cost": "Test_Time_Compute_Cost",
    "data quality": "Data_Quality"
}

def map_method_to_link(tag: str) -> str:
    clean = re.sub(r"[^\w\s-]", "", tag).lower().strip()
    if clean in KNOWN_METHODS:
        return f"[[{KNOWN_METHODS[clean]}]]"
    for key, page in KNOWN_METHODS.items():
        if key in clean or clean in key:
            return f"[[{page}]]"
    return None

def map_problem_to_link(tag: str) -> str:
    clean = re.sub(r"[^\w\s-]", "", tag).lower().strip()
    if clean in KNOWN_PROBLEMS:
        return f"[[{KNOWN_PROBLEMS[clean]}]]"
    for key, page in KNOWN_PROBLEMS.items():
        if key in clean or clean in key:
            return f"[[{page}]]"
    return None

class NoteGenerator:
    @staticmethod
    def clean_migrated_content(text: str) -> str:
        if not text:
            return ""
        # Remove HTML comment markers
        text = re.sub(r"<!--\s*START_\w+\s*-->", "", text)
        text = re.sub(r"<!--\s*END_\w+\s*-->", "", text)
        
        has_callout = bool(re.search(r"^>\s*\[\!.*?\]", text, re.MULTILINE))
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if has_callout:
                # Skip Obsidian callout headers
                if re.match(r"^>\s*\[\!.*?\]", stripped):
                    continue
                # Skip warning boilerplate lines
                if stripped.startswith(">") and ("绝对禁止覆盖" in stripped or "自动更新不会覆盖" in stripped or "任何自动同步工具" in stripped or "我的精读笔记" in stripped or "我的独立技术判断" in stripped or "人工" in stripped):
                    continue
                # Remove block quote leading marker inside callouts
                if stripped.startswith(">"):
                    line = re.sub(r"^>\s?", "", line)
            cleaned_lines.append(line)
            
        return "\n".join(cleaned_lines).strip()

    @staticmethod
    def is_top_level_header(line: str) -> bool:
        line = line.strip()
        if not (line.startswith("##") and not line.startswith("###")):
            return False
        title = line[2:].strip()
        norm_title = normalize_heading(title)
        
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
        return norm_title in headers

    @staticmethod
    def extract_section(content: str, header_title: str) -> str:
        """
        Robustly extracts section content starting from the specified ## heading
        until the next H2 heading (starting with ## but not ###).
        """
        if not content:
            return None
        
        lines = content.splitlines()
        target_norm = normalize_heading(header_title)
        
        for idx, line in enumerate(lines):
            line_str = line.strip()
            if line_str.startswith("##") and not line_str.startswith("###"):
                title_part = line_str[2:].strip()
                norm_title = normalize_heading(title_part)
                if norm_title == target_norm:
                    # Find the end of this section (only stop at another H2 heading)
                    end_idx = len(lines)
                    for j in range(idx + 1, len(lines)):
                        next_line = lines[j].strip()
                        if next_line.startswith("##") and not next_line.startswith("###"):
                            end_idx = j
                            break
                    section_lines = lines[idx + 1:end_idx]
                    section_content = "\n".join(section_lines).strip()
                    # Clean horizontal rule and backlink footer if it was captured at the end of document
                    if end_idx == len(lines):
                        section_content = re.sub(r"\s*---\s*\*回到主入口:.*?\*\s*$", "", section_content, flags=re.IGNORECASE).strip()
                    return section_content
        return None

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
        source = paper.get("source")
        status = paper.get("status")
        # Normalize Source / Status / Data Origin consistency
        if data_origin == "openreview_api":
            source = "openreview"
            status = "accepted"
        elif data_origin == "fallback_fixture":
            source = "openreview"
            status = "accepted"
        else:
            if not source or str(source).strip().lower() in ("", "unknown", "none"):
                source = "Unknown"
            if not status or str(status).strip().lower() in ("", "unknown", "none"):
                status = "Unknown"
        
        # Format tags
        method_tags_str = format_tags_list(paper.get("post_training_types", []))
        problem_tags_str = format_tags_list(paper.get("problem_tags", []))
        model_type_tag = format_tag(paper.get('model_type', 'Other'))
        unread_tag = format_tag('Unread')
        
        # 1. Build Auto Metadata Markdown Table
        metadata_rows = [
            f"| Venue | {paper.get('venue', 'Unknown')} |",
            f"| Year | {paper.get('year', 2025)} |",
            f"| Authors | {authors_str} |",
            f"| Source | {source} |",
            f"| Status | {status} |",
            f"| Data Origin | {data_origin} |",
            f"| Type | {model_type_tag} |",
            f"| Tags | {unread_tag} |",
            f"| Priority | {paper.get('priority', 'Medium')} |",
            f"| Relevance Level | {paper.get('relevance_level', 'D_Irrelevant')} |",
            f"| Confidence | {paper.get('confidence', 0.0)} |",
            f"| Reason | {paper.get('reason', 'No reason provided.')} |",
            f"| Method Tags | {method_tags_str} |",
            f"| Problem Tags | {problem_tags_str} |",
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
            classification_evidence_table = (
                "| Section | Keyword Group | Title Matches | Abstract Matches | Evidence Detail |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                "| - | - | - | - | No classification evidence recorded. |"
            )

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

        if existing_content and existing_content.strip():
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

            # Clean migrated content for all extracted sections
            if old_metadata is not None: old_metadata = self.clean_migrated_content(old_metadata)
            if old_ai_draft is not None: old_ai_draft = self.clean_migrated_content(old_ai_draft)
            if old_evidence is not None: old_evidence = self.clean_migrated_content(old_evidence)
            if old_review is not None: old_review = self.clean_migrated_content(old_review)
            if old_notes is not None: old_notes = self.clean_migrated_content(old_notes)
            if old_judgment is not None: old_judgment = self.clean_migrated_content(old_judgment)
            if old_extraction is not None: old_extraction = self.clean_migrated_content(old_extraction)
            if old_backfeed is not None: old_backfeed = self.clean_migrated_content(old_backfeed)
            if old_share is not None: old_share = self.clean_migrated_content(old_share)
            if old_next_action is not None: old_next_action = self.clean_migrated_content(old_next_action)

        # 3. Handle Safe Sync Override logic per section

        # AI Draft Summary
        abstract_val = paper.get("abstract") or ""
        abstract_val = str(abstract_val).strip()
        if abstract_val and abstract_val not in ("...", "") and len(abstract_val) > 5:
            clean_abstract = " ".join(abstract_val.split())
            if len(clean_abstract) > 300:
                problem_solved = f"{clean_abstract[:300]}..."
            else:
                problem_solved = clean_abstract
        else:
            problem_solved = "待精读后补充"

        if old_ai_draft and not overwrite:
            ai_draft_content = old_ai_draft
        else:
            ai_draft_content = f"""*   **一句话总结**: 作者认为 ______，因此提出 ______。
*   **解决的问题**: {problem_solved}
*   **核心方法**: 
*   **实验结论**: """

        # Classification Evidence
        if old_evidence and not overwrite:
            evidence_content = old_evidence
        else:
            evidence_content = classification_evidence_table

        # My Reading Notes (Protected - Never Overwritten)
        if old_notes:
            notes_content = old_notes
        else:
            notes_content = """> 说明：这里是人工精读笔记区，任何自动同步均不会覆盖此区。
*   **阅读时间**: 
*   **精读笔记**: 
    *   (在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)"""

        # My Judgment (Protected - Never Overwritten)
        if old_judgment:
            judgment_content = old_judgment
        else:
            judgment_content = """> 说明：这里是人工独立技术判断区，任何自动同步均不会覆盖此区。
*   **论文盲点/局限性**: 
*   **实验设计局限**: 
*   **我的评价**: 
    *   (在这里写下您对该文的真实技术评价，是否真正解决了痛点？)"""

        # AI Draft Review (Protected - Never Overwritten)
        if old_review:
            review_content = old_review
        else:
            review_content = """> 说明：人工对 AI 生成草稿的审查记录，自动更新不会覆盖。
*   **AI Draft 是否可信**: High / Medium / Low
*   **错误点**: 
*   **我修正后的理解**: 
*   **是否需要重新生成**: """

        # Knowledge Extraction (Overwrite/Regenerate or Preserve)
        def parse_tags_to_list(tags_input) -> list:
            if not tags_input:
                return []
            if isinstance(tags_input, str):
                tags_input = tags_input.strip()
                if not tags_input:
                    return []
                if tags_input.startswith("[") and tags_input.endswith("]"):
                    try:
                        parsed = json.loads(tags_input)
                        if isinstance(parsed, list):
                            return parsed
                    except Exception:
                        pass
                return [t.strip() for t in re.split(r"[/,]", tags_input) if t.strip()]
            if isinstance(tags_input, list):
                flat = []
                for item in tags_input:
                    if isinstance(item, str):
                        parts = re.split(r"[/,]", item)
                        flat.extend([p.strip() for p in parts if p.strip()])
                    else:
                        flat.append(item)
                return flat
            return [tags_input]

        method_tags = parse_tags_to_list(paper.get("post_training_types", []))
        method_links = []
        for t in method_tags:
            link = map_method_to_link(str(t))
            if link:
                method_links.append(link)
        
        problem_tags = parse_tags_to_list(paper.get("problem_tags", []))
        problem_links = []
        for t in problem_tags:
            link = map_problem_to_link(str(t))
            if link:
                problem_links.append(link)
        
        method_links_str = " ".join(sorted(list(set(method_links)))) if method_links else "待人工补充"
        problem_links_str = " ".join(sorted(list(set(problem_links)))) if problem_links else "待人工补充"

        if old_extraction and not overwrite:
            extraction_content = old_extraction
        else:
            extraction_content = f"""*   **可提炼的方法/技术路线**: ➔ {method_links_str}
*   **可引入的问题意识/技术冲突**: ➔ {problem_links_str}
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
            next_action_content = """*   [ ] 读 Introduction
*   [ ] 读 Method
*   [ ] 读 Experiments
*   [ ] 看 Ablation
*   [ ] 找相关论文对比
*   [ ] 回流到知识页
*   [ ] 判断是否生成分享稿"""

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
