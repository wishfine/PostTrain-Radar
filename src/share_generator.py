import re

class ShareGenerator:
    @staticmethod
    def extract_section(content: str, start_marker: str, end_marker: str) -> str:
        pattern = re.escape(start_marker) + r"(.*?)" + re.escape(end_marker)
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def generate(self, paper: dict, existing_content: str = None) -> str:
        """
        Generates or updates a paper share brief markdown text.
        """
        post_train_str = ", ".join(paper.get("post_training_types", []))
        prob_tags_str = ", ".join(paper.get("problem_tags", []))
        data_origin = paper.get("data_origin", "openreview_api")
        
        title = paper.get('title', '')
        cn_title_suggestion = f"[分享译名] {title}"
        if "direct preference optimization" in title.lower() or "dpo" in title.lower():
            cn_title_suggestion = f"【后训练】直接偏好优化新进展：{title}"
        elif "grpo" in title.lower() or "group relative" in title.lower():
            cn_title_suggestion = f"【强化学习】突破 Critic 显存瓶颈的 GRPO 实战：{title}"
        elif "reasoning" in title.lower():
            cn_title_suggestion = f"【推理模型】大模型 Reasoning 能力的强化路径：{title}"

        metadata_content = f"""- Original Title: {title}
- Venue: {paper.get('venue')}
- Year: {paper.get('year')}
- Model Type: {paper.get('model_type', 'Other')}
- Post-training Type: {post_train_str}
- Problem Tags: {prob_tags_str}
- Data Origin: {data_origin}
- Relevance Level: {paper.get('relevance_level', 'D_Irrelevant')}
- Core Post-Training: {"Yes" if paper.get('is_core_posttraining') else "No"}
- URL: {paper.get('paper_url') or 'N/A'}
- PDF: {paper.get('pdf_url') or 'N/A'}"""

        audience_list = []
        if "VLM" in paper.get('model_type', ''):
            audience_list.append("- VLM / 多模态对齐方向研究者")
        if "Agent" in paper.get('model_type', ''):
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
            my_share_content = self.extract_section(existing_content, "<!-- START_MY_SHARE_DETAILS -->", "<!-- END_MY_SHARE_DETAILS -->")
            my_sources_content = self.extract_section(existing_content, "<!-- START_SOURCES -->", "<!-- END_SOURCES -->")

        if not my_share_content:
            my_share_content = f"""## 📝 分享标题
{cn_title_suggestion}

## ⚡ 30 秒概括
这篇论文主要讲：

## 👥 适合什么听众？
{audience_str}

## ⚡ 5-Minute Elevator Pitch (5分钟闪电演讲大纲)
1. **核心痛点**：过去方法（如 SFT）有什么硬伤？
2. **核心思想**：作者用什么最直观的招数解决了它？
3. **最强战绩**：提升了多少？最亮眼的实验数据是什么？

## 🛠️ 15-Minute Technical Session (15分钟组会分享大纲)
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

## 🔬 30-Minute Deep Dive Seminar (30分钟深度研讨大纲)
1. **深入方法与公式分析**：
   - 细致剖析损失函数（Loss Function）或理论推导逻辑。
2. **工程实现细节与踩坑分析**：
   - 代码复现时的可能坑点，或是数据质量清洗逻辑。
3. **前沿技术路线横向对比**：
   - 该方法和已有主流 DPO / PPO / GRPO 方法的路线图技术演进对比。
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

## 1. Auto Metadata
<!-- START_AUTO_METADATA -->
{metadata_content}
<!-- END_AUTO_METADATA -->

## 2. My Share Content
<!-- START_MY_SHARE_DETAILS -->
{my_share_content}
<!-- END_MY_SHARE_DETAILS -->

## 3. Sources / 来源溯源
<!-- START_SOURCES -->
{my_sources_content}
<!-- END_SOURCES -->
"""
        return share_brief
