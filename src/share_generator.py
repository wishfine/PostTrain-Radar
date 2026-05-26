import re

def normalize_heading(title_str: str) -> str:
    # Strip brackets, emojis, and punctuation, leaving letters, numbers, spaces, and Chinese characters
    t = title_str.strip("[]").strip()
    t = re.sub(r"[^\w\s\u4e00-\u9fa5]", "", t).strip()
    return t.lower()

class ShareGenerator:
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

    def generate(self, paper: dict, existing_content: str = None) -> str:
        post_train_str = ", ".join(paper.get("post_training_types", []))
        prob_tags_str = ", ".join(paper.get("problem_tags", []))
        data_origin = paper.get("data_origin", "openreview_api")
        
        title = paper.get("title", "")
        cn_title_suggestion = f"[分享译名] {title}"
        if "direct preference optimization" in title.lower() or "dpo" in title.lower():
            cn_title_suggestion = f"【后训练】直接偏好优化新进展：{title}"
        elif "grpo" in title.lower() or "group relative" in title.lower():
            cn_title_suggestion = f"【强化学习】突破 Critic 显存瓶颈的 GRPO 实战：{title}"
        elif "reasoning" in title.lower():
            cn_title_suggestion = f"【推理模型】大模型 Reasoning 能力的强化路径：{title}"
 
        metadata_content = f"""- Original Title: {title}
- Venue: {paper.get("venue")}
- Year: {paper.get("year")}
- Model Type: {paper.get("model_type", "Other")}
- Post-training Type: {post_train_str}
- Problem Tags: {prob_tags_str}
- Data Origin: {data_origin}
- Relevance Level: {paper.get("relevance_level", "D_Irrelevant")}
- Core Post-Training: {"Yes" if paper.get("is_core_posttraining") else "No"}
- URL: {paper.get("paper_url") or "N/A"}
- PDF: {paper.get("pdf_url") or "N/A"}"""
 
        audience_list = []
        if "VLM" in paper.get("model_type", ""):
            audience_list.append("- VLM / 多模态对齐方向研究者")
        if "Agent" in paper.get("model_type", ""):
            audience_list.append("- AI Agent / 动作空间强化学习方向研究者")
        if any(t in post_train_str for t in ["DPO", "Preference"]):
            audience_list.append("- 偏好对齐 (DPO/Preference Optimization) 关注者")
        if any(t in post_train_str for t in ["GRPO", "Reasoning"]):
            audience_list.append("- Reasoning RL / 逻辑推理强化学习关注者")
        if not audience_list:
            audience_list.append("- LLM Post-training 通用方向研究员")
        audience_str = "\n".join(audience_list)
 
        my_share_content = ""
        my_sources_content = ""
        if existing_content:
            my_share_content = self.extract_section(existing_content, "My Share Content")
            my_sources_content = self.extract_section(existing_content, "Sources")
            
            if my_share_content is not None:
                my_share_content = self.clean_migrated_content(my_share_content)
            if my_sources_content is not None:
                my_sources_content = self.clean_migrated_content(my_sources_content)
 
        if not my_share_content:
            my_share_content = f"""### 分享标题
{cn_title_suggestion}
 
### 30 秒概括
这篇论文主要讲：
 
### 适合什么听众
{audience_str}
 
### 5-Minute Elevator Pitch (5分钟闪电演讲大纲)
1. **核心痛点**：过去方法（如 SFT）有什么硬伤？
2. **核心思想**：作者用什么最直观的招数解决了它？
3. **最强战绩**：提升了多少？最亮眼的实验数据是什么？
 
### 15-Minute Technical Session (15分钟组会分享大纲)
1. **背景问题与关键矛盾**：
   - 详细剖析面临的方法瓶颈（如 DPO 的 Length Bias，或者 GRPO 的 Sampling 消耗）。
2. **方法拆解**：
   - 步骤一：
   - 步骤二：
   - 步骤三：
3. **核心实验与消融分析**：
   - 关键对比的 Baseline 是谁？消融实验说明了什么？
4. **我的评价与思考**：
   - 它的创新是真实的吗？在工程上好部署吗？
 
### 30-Minute Deep Dive Seminar (30分钟深度研讨大纲)
1. **深入方法与公式分析**：
   - 细致剖析损失函数（Loss Function）或理论推导逻辑。
2. **工程实现细节与踩坑分析**：
   - 代码复现时的可能坑点，或是数据质量清洗逻辑。
3. **前沿技术路线横向对比**：
   - 该方法 and 已有主流 DPO / PPO / GRPO 方法的路线图技术演进对比。
4. **开放式问题讨论**：
   - 引导组会讨论的 3 个问题：
     - 问题1：
     - 问题2：
     - 问题3："""
 
        if not my_sources_content:
            my_sources_content = f"""- **观点来源**: 
- **论文来源**: [[{title}]]
- **方法页来源**: 
- **问题页来源**: 
- **内部链接来源**: """
 
        share_brief = f"""# Paper Share Brief: {title}
 
## Auto Metadata
{metadata_content}
 
## My Share Content
{my_share_content}
 
## Sources
{my_sources_content}"""
        return share_brief
