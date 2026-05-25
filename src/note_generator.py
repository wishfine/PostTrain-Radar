import re
import json

class NoteGenerator:
    @staticmethod
    def extract_section(content: str, start_marker: str, end_marker: str) -> str:
        """
        Extracts content between HTML comment markers.
        """
        pattern = re.escape(start_marker) + r"(.*?)" + re.escape(end_marker)
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def generate(self, paper: dict, existing_content: str = None) -> str:
        """
        Generates or updates a paper reading note markdown text.
        If existing_content is provided, preserves sections inside human markers.
        """
        # Formulate Auto Metadata section
        authors_str = ", ".join(paper.get("authors", []))
        post_train_str = ", ".join(paper.get("post_training_types", []))
        prob_tags_str = ", ".join(paper.get("problem_tags", []))
        data_origin = paper.get("data_origin", "openreview_api")
        
        metadata_content = f"""- Title: {paper.get('title')}
- Venue: {paper.get('venue')}
- Year: {paper.get('year')}
- Authors: {authors_str}
- URL: {paper.get('paper_url') or 'N/A'}
- PDF: {paper.get('pdf_url') or 'N/A'}
- Model Type: {paper.get('model_type', 'Other')}
- Post-training Type: {post_train_str}
- Problem Tags: {prob_tags_str}
- Data Origin: {data_origin}
- Reading Status: {paper.get('reading_status', 'Unread')}
- Priority: {paper.get('priority', 'Medium')}
- Share Status: {paper.get('share_status', 'Not Started')}
- My Rating: {paper.get('my_rating') or ''}
- Next Action: {paper.get('next_action') or ''}"""

        # Formulate AI Draft section
        kws_matched = ", ".join(paper.get("keywords_matched", []))
        matched_evidence = paper.get("matched_evidence", {})
        evidence_lines = []
        if isinstance(matched_evidence, dict):
            for section, details in matched_evidence.items():
                if details:
                    lines = []
                    for label, kws in details.items():
                        lines.append(f"    - **{label}**: {kws}")
                    evidence_lines.append(f"  - *{section}*:\n" + "\n".join(lines))
        evidence_str = "\n".join(evidence_lines) if evidence_lines else "  - None"

        ai_draft_content = f"""### Heuristic Scorer Result
- Relevance: {"Relevant" if paper.get("is_relevant") else "Not Relevant"}
- Confidence Score: {paper.get("confidence", 0.0)}
- Reason: {paper.get("reason", "No reason provided.")}
- Keywords Matched: {kws_matched}
- Matched Evidence:
{evidence_str}"""

        # Retrieve human sections or create default templates
        my_notes_content = ""
        my_judgment_content = ""

        if existing_content:
            my_notes_content = self.extract_section(existing_content, "<!-- START_MY_NOTES -->", "<!-- END_MY_NOTES -->")
            my_judgment_content = self.extract_section(existing_content, "<!-- START_MY_JUDGMENT -->", "<!-- END_MY_JUDGMENT -->")

        if not my_notes_content:
            my_notes_content = """### 这篇论文想解决什么问题？
用我自己的话写，而不是复制摘要。

### 为什么这个问题重要？
从 LLM/VLM post-training 的角度说明。

### 过去方法有什么不足？
关注：
- SFT 是否不足？
- RLHF 是否成本高？
- DPO/GRPO 是否有偏差？
- Reward model 是否不稳定？
- VLM 是否存在视觉-语言对齐问题？
- reasoning 是否存在训练/推理不一致？

### 这篇论文的核心思想是什么？
用一句话概括：
“作者认为 ______，因此提出 ______。”

### 方法部分怎么做？
请拆成 3-5 个步骤：
1. 
2. 
3. 
4. 
5. 

### 核心创新点
至少总结 3 点：
1. 
2. 
3. 

### 实验验证了什么？
关注：
- baseline 是谁？
- benchmark 是什么？
- 主要提升在哪里？
- ablation 说明了什么？
- 是否有泛化实验？"""

        if not my_judgment_content:
            my_judgment_content = """### 我怎么看这篇论文？
从以下角度批判性分析：
- 这个方法真正解决了什么？
- 它有没有把问题简化？
- 它依赖什么假设？
- 它和已有 DPO / RLHF / GRPO / SFT 方法相比，真正不同在哪里？
- 它适合 LLM / VLM / Video-LMM 吗？
- 是否可以迁移到 agent / reasoning / multimodal 场景？

### 可以分享给别人的核心观点
请整理成 3 条适合分享的观点：
1. 
2. 
3. 

### 我后续可以追的问题
1. 
2. 
3. """

        # Stitch everything together with explicit markers
        note = f"""# Paper Reading Note: {paper.get('title')}

## 1. Auto Metadata
<!-- START_AUTO_METADATA -->
{metadata_content}
<!-- END_AUTO_METADATA -->

## 2. AI Draft
<!-- START_AI_DRAFT -->
{ai_draft_content}
<!-- END_AI_DRAFT -->

## 3. My Notes
<!-- START_MY_NOTES -->
{my_notes_content}
<!-- END_MY_NOTES -->

## 4. My Judgment
<!-- START_MY_JUDGMENT -->
{my_judgment_content}
<!-- END_MY_JUDGMENT -->
"""
        return note
