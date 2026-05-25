import requests
import json
import time

API_URL = "http://127.0.0.1:6806"
API_TOKEN = "bqrrmb48o36gbpo2"
NOTEBOOK_NAME = "PostTrain_Radar"

def call_api(endpoint, data):
    url = f"{API_URL}{endpoint}"
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error calling {endpoint}: {e}")
        return None

def get_or_create_notebook(name):
    print(f"Listing notebooks to find '{name}'...")
    res = call_api("/api/notebook/lsNotebooks", {})
    if res and res.get("code") == 0:
        notebooks = res.get("data", {}).get("notebooks", [])
        for nb in notebooks:
            if nb.get("name") == name:
                print(f"  [+] Found existing notebook '{name}' (ID: {nb.get('id')})")
                return nb.get("id")
    
    print(f"Notebook '{name}' not found. Creating a new one...")
    create_res = call_api("/api/notebook/createNotebook", {"name": name})
    if create_res and create_res.get("code") == 0:
        data = create_res.get("data")
        nb_id = None
        if isinstance(data, str):
            nb_id = data
        elif isinstance(data, dict):
            nb_id = data.get("id") or data.get("notebook", {}).get("id")
        
        if nb_id:
            print(f"  [+] Created new notebook '{name}' (ID: {nb_id})")
            # Wait a moment for notebook to initialize
            time.sleep(2)
            return nb_id
    
    print(f"  [!] Failed to create notebook: {create_res}")
    return None

def create_doc(notebook_id, path, md_content=""):
    print(f"Creating doc: {path}...")
    res = call_api("/api/filetree/createDocWithMd", {
        "notebook": notebook_id,
        "path": path,
        "markdown": md_content
    })
    if res and res.get("code") == 0:
        print(f"  [+] Success (ID: {res.get('data')})")
        return res.get("data")
    else:
        print(f"  [!] Failed: {res}")
        return None

def main():
    print("=== Starting SiYuan V3 Note Workspace Rebuild ===")

    # Resolve Notebook ID dynamically
    notebook_id = get_or_create_notebook(NOTEBOOK_NAME)
    if not notebook_id:
        print("[!] Critical Error: Could not resolve or create notebook.")
        return

    # 1. Root Directories / Placeholders
    # 00_Index
    create_doc(notebook_id, "/00_Index", "# 🧭 00_Index\n\n索引与入口中心。")
    # 01_Papers
    create_doc(notebook_id, "/01_Papers", "# 📚 01_Papers\n\n精选论文卡片存储目录。")
    # 02_Topics
    create_doc(notebook_id, "/02_Topics", "# 🔬 02_Topics\n\n研究专题沉淀。")
    # 03_Methods
    create_doc(notebook_id, "/03_Methods", "# 🛠️ 03_Methods\n\n具体方法机制解构。")
    # 04_Problems
    create_doc(notebook_id, "/04_Problems", "# ⚠️ 04_Problems\n\n研究痛点与问题意识库。")
    # 05_Share
    create_doc(notebook_id, "/05_Share", "# 📝 05_Share\n\n分享材料与输出中心。")
    # 06_Workflows
    create_doc(notebook_id, "/06_Workflows", "# ⚙️ 06_Workflows\n\n规范流程与提示词库。")
    # 99_Archive
    create_doc(notebook_id, "/99_Archive", "# 📦 99_Archive\n\n归档与历史备份区。")

    # 2. 00_Index Pages
    total_portal_md = """# 🧭 总入口 (PostTrain Radar Entry)

> [!IMPORTANT]
> **思源知识库定位**：本笔记**绝对不是全量论文仓库**，而是一个面向 LLM/VLM post-training 领域的**精选阅读工作台**。全量论文的抓取、过滤与分类结果由 PostTrain Radar 项目在 SQLite 和本地 CSV 报告中存储与维护。

## 三层模型说明

本知识库采用“输入 - 知识 - 输出”三层模型闭环，促进论文原材料转化为长期学术/工程洞察：

1. **输入层 (01_Papers)**：从 PostTrain Radar 项目同步来的少量精选论文卡片，包含 AI 草稿与元数据，用于人工精读与批判。
2. **知识层 (02_Topics / 03_Methods / 04_Problems)**：将论文解构回流，沉淀到专题、具体方法机制以及痛点问题的**[来自论文阅读的思考]**区域中。
3. **输出层 (05_Share)**：将知识沉淀整合，生成组会分享、技术博客与 PPT 大纲。

```mermaid
graph TD
    A[Papers 输入层] -->|阅读 & 知识提取| B(Topics / Methods / Problems 知识层)
    B -->|提炼 & 组装| C[Share 输出层]
```

## 🏷️ 标准标签系统

目录负责主结构；标签负责横向筛选；双链负责知识连接。

### Model Type (模型类型)
- `#LLM` - 纯语言大模型
- `#VLM` - 视觉-文本多模态模型
- `#VideoLMM` - 视频-文本大模型
- `#Agent` - 智能体与工具使用对齐

### Method Type (方法机制)
- `#SFT` - 监督微调
- `#RLHF` - 基于人类反馈强化学习
- `#DPO` - 直接偏好优化
- `#GRPO` - 组相对策略优化
- `#RewardModel` - 奖励模型 (ORM/PRM)
- `#Verifier` - 规则验证器 (Math/Code)
- `#TestTimeScaling` - 推理期计算量缩放
- `#MultimodalAlignment` - 多模态对齐

### Problem Type (研究痛点)
- `#RewardHacking` - 奖励作弊
- `#LengthBias` - 长度偏见、答案冗长
- `#CreditAssignment` - 信用分配、延迟反馈
- `#DistributionShift` - 离线分布偏移
- `#Hallucination` - 幻觉与对齐损失
- `#Grounding` - 细粒度定位失败
- `#EvaluationLeakage` - 评测集泄漏

### Reading Status (阅读状态)
- `#Unread` - 待读
- `#Skimmed` - 扫读/粗读
- `#Reading` - 正在精读
- `#Finished` - 精读完毕并沉淀思考
- `#WorthSharing` - 强烈推荐分享
- `#Shared` - 已分享过

### Share Value (分享价值)
- `#Conceptual` - 思想级创新
- `#Methodological` - 方法与公式级创新
- `#Experimental` - 实验与数据突破
- `#SurveyWorthy` - 全景式综述
- `#RelatedToMyResearch` - 必须彻底复现的强相关研究

## 🔄 推荐使用流程

1. **抓取分类**：运行 PostTrain Radar 完成全量论文抓取与分类。
2. **人工筛选**：在 SQLite/CSV 报告中筛选高价值论文（在 `tag_overrides.yaml` 中标记 `include_in_siyuan: true`）。
3. **精选同步**：运行同步逻辑，仅将精选论文卡片同步至 `01_Papers` 对应目录。
4. **人工精读**：阅读论文并填写 `My Reading Notes`、`My Judgment` 和 `AI Draft Review`。
5. **知识回流**：通过双链将提炼观点手工回流至对应的 Topic/Method/Problem 页面中。
6. **成果分享**：利用 `05_Share` 模板将多维知识拼装为分享大纲。

---
*回到主入口: [[总入口]]*"""
    create_doc(notebook_id, "/00_Index/总入口", total_portal_md)

    create_doc(notebook_id, "/00_Index/LLM Post-training 路线图", "# LLM Post-training 路线图\n\n用于描绘 LLM 监督微调 (SFT)、强化学习对齐 (RLHF/DPO/GRPO) 的演进路线与重要论文。")
    create_doc(notebook_id, "/00_Index/VLM Post-training 路线图", "# VLM Post-training 路线图\n\n用于描绘多模态指令微调与偏好对齐技术路线。")

    reading_queue_md = """# 待读论文队列

这是未来由 PostTrain Radar 项目同步的索引页。以下为同步模板结构：

| Paper | Venue | Method | Problem | Priority | Reading Status | Next Action |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| *（示例）* [[SimPO - Simple Preference Optimization]] | ArXiv | DPO | Length Bias | High | Unread | 读 Method |
"""
    create_doc(notebook_id, "/00_Index/待读论文队列", reading_queue_md)

    featured_queue_md = """# 精选阅读队列

本页面展示我人工筛选、真正要深读的论文队列。

| Paper | Why Selected | Method | Problem | Share Value | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| *（示例）* [[DeepSeekMath]] | 提出 GRPO，大幅节省强化学习 Critic 显存 | GRPO | Credit Assignment | #Methodological | Reading |
"""
    create_doc(notebook_id, "/00_Index/精选阅读队列", featured_queue_md)

    thoughts_index_md = """# 阅读后思考索引

## 最近完成阅读

| Paper | Venue | Method | Problem | My Judgment | Backfeed Status | Share Value |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| *（示例）* [[SimPO]] | ArXiv | DPO | Length Bias | Margin 机制惩罚冗长效果好，但参数较敏感 | [x] 已回流 | #Methodological |

## 值得回流的观点

| Insight | From Paper | Target Page | Status |
| :--- | :--- | :--- | :---: |
| GRPO 组内标准化充当 Baseline，省去 Critic 网络 | [[DeepSeekMath]] | [[GRPO]] | [ ] 待回流 |

## 值得分享的选题

| Topic | Source Papers | Duration | Status |
| :--- | :--- | :--- | :---: |
| 偏好对齐方法中 Length Bias 的成因与消解方案 | [[SimPO]], [[DPO]] | 30min | [ ] 待分享 |
"""
    create_doc(notebook_id, "/00_Index/阅读后思考索引", thoughts_index_md)

    backflow_md = """# 知识回流建议

本页面由项目生成或人工整理，列出推荐回流至核心知识页的论文和观点。

## 待回流 Topic 的观点
- 

## 待回流 Method 的观点
- 

## 待回流 Problem 的观点
- 

## 待进入 Share 候选池的观点
- 
"""
    create_doc(notebook_id, "/00_Index/知识回流建议", backflow_md)
    create_doc(notebook_id, "/00_Index/已分享内容索引", "# 已分享内容索引\n\n记录已经在组会、技术博客等渠道分享过的成果大纲与链接。")

    # 3. 01_Papers subdirectories & Template
    create_doc(notebook_id, "/01_Papers/ICLR_2025", "# ICLR 2025\n\nConfirmed accepted conference papers for ICLR 2025.")
    create_doc(notebook_id, "/01_Papers/NeurIPS_2025", "# NeurIPS 2025\n\nConfirmed accepted conference papers for NeurIPS 2025.")
    create_doc(notebook_id, "/01_Papers/ICML_2025", "# ICML 2025\n\nConfirmed accepted conference papers for ICML 2025.")
    create_doc(notebook_id, "/01_Papers/ACL_2025", "# ACL 2025\n\nConfirmed accepted conference papers for ACL 2025.")
    create_doc(notebook_id, "/01_Papers/EMNLP_2025", "# EMNLP 2025\n\nConfirmed accepted conference papers for EMNLP 2025.")
    create_doc(notebook_id, "/01_Papers/CVPR_2025", "# CVPR 2025\n\nConfirmed accepted conference papers for CVPR 2025.")
    create_doc(notebook_id, "/01_Papers/ICCV_2025", "# ICCV 2025\n\nConfirmed accepted conference papers for ICCV 2025.")
    create_doc(notebook_id, "/01_Papers/ArXiv_Preprints", "# ArXiv Preprints\n\nArXiv preprints or unconfirmed publications.")
    create_doc(notebook_id, "/01_Papers/Manual_Import", "# Manual Import\n\nManually imported papers without verified venue.")

    paper_card_md = """# Paper Title

## Auto Metadata
<!-- START_AUTO_METADATA -->
- Title:
- Authors:
- Venue:
- Year:
- Source:
- Source ID:
- Data Origin:
- Status:
- Model Type:
- Method Tags:
- Problem Tags:
- Relevance Level:
- Priority:
- Reading Status:
- Share Status:
- Paper URL:
- PDF URL:
- Synced At:
- Sync Mode:
<!-- END_AUTO_METADATA -->

> 说明：这一部分可以由 PostTrain Radar 自动生成或更新。

---

## AI Draft Summary
<!-- START_AI_DRAFT_SUMMARY -->
### 一句话总结

作者认为 ______，因此提出 ______。

### 核心问题

### 方法思路

### 实验结论

### Matched Evidence
<!-- END_AI_DRAFT_SUMMARY -->

> 说明：这一部分可以由 AI 辅助生成，但需要人工检查。

---

## My Reading Notes
<!-- START_MY_READING_NOTES -->
> 这是我的人工阅读笔记，任何自动同步都不能覆盖。

### 1. 我为什么读这篇论文？

### 2. 读完后我真正理解了什么？

### 3. 这篇论文最有价值的点是什么？

### 4. 我觉得它没有讲清楚什么？

### 5. 我不同意或怀疑的地方
<!-- END_MY_READING_NOTES -->

---

## My Judgment
<!-- START_MY_JUDGMENT -->
> 这是我的最终判断，任何自动同步都不能覆盖。

### 这篇论文的真实贡献

### 它是否只是工程组合？

### 它和已有路线的关系

- SFT:
- RLHF / PPO:
- DPO:
- GRPO:
- Reward Model / Verifier:
- VLM Alignment:

### 我的批判性评价
<!-- END_MY_JUDGMENT -->

---

## AI Draft Review
<!-- START_AI_DRAFT_REVIEW -->
> 这是我对 AI 初稿质量的检查，任何自动同步都不能覆盖。

- AI Draft 是否可信：High / Medium / Low
- AI 错误点：
- 我修正后的理解：
- 是否需要重新生成：
<!-- END_AI_DRAFT_REVIEW -->

---

## Knowledge Extraction
<!-- START_KNOWLEDGE_EXTRACTION -->
### 应该链接到的 Topic 页面

- [[LLM_PostTraining]]
- [[VLM_PostTraining]]
- [[Agent_PostTraining]]

### 应该链接到的 Method 页面

- [[DPO]]
- [[GRPO]]
- [[RLHF]]
- [[Reward_Modeling]]

### 应该链接到的 Problem 页面

- [[Credit_Assignment]]
- [[Length_Bias]]
- [[Reward_Hacking]]
- [[Distribution_Shift]]

### 可复用知识点

- 一个概念：
- 一个问题：
- 一个方法机制：
- 一个实验设计经验：
- 一个批判性观点：
<!-- END_KNOWLEDGE_EXTRACTION -->

---

## Knowledge Backfeed Status
<!-- START_KNOWLEDGE_BACKFEED_STATUS -->
- [ ] 已回流 Topic 页面
- [ ] 已回流 Method 页面
- [ ] 已回流 Problem 页面
- [ ] 已加入 Share 候选池
- [ ] 已更新 阅读后思考索引
<!-- END_KNOWLEDGE_BACKFEED_STATUS -->

---

## Share Decision
<!-- START_SHARE_DECISION -->
- 是否值得分享：Yes / No / Maybe
- 分享价值：Conceptual / Methodological / Experimental / Survey-worthy / Related-to-my-research
- 适合分享时长：5min / 15min / 30min
- 分享角度：
- 目标听众：
<!-- END_SHARE_DECISION -->

---

## Next Action
<!-- START_NEXT_ACTION -->
- [ ] 读 Introduction
- [ ] 读 Method
- [ ] 读 Experiments
- [ ] 看 Ablation
- [ ] 找相关论文对比
- [ ] 回流到知识页
- [ ] 生成分享稿
- [ ] 归档
<!-- END_NEXT_ACTION -->

---
*回到主入口: [[总入口]]*"""
    create_doc(notebook_id, "/01_Papers/Paper_Card_Template", paper_card_md)

    # 4. 02_Topics Pages
    topic_template = """# {name}

## 基本定义

## 为什么这个主题重要？

## 核心问题

## 代表论文

## 相关方法

## 主要争议

## 来自论文阅读的思考

> 这里记录我从多篇论文中沉淀出的个人理解，不是论文摘要堆砌。

## 我自己的判断

## 可分享观点

## 相关页面

---
*回到主入口: [[总入口]]*"""

    # Subdirectories for Topics
    create_doc(notebook_id, "/02_Topics/LLM_PostTraining", "# LLM PostTraining\n\n大语言模型后训练专题")
    create_doc(notebook_id, "/02_Topics/VLM_PostTraining", "# VLM PostTraining\n\n视觉大语言模型后训练专题")
    create_doc(notebook_id, "/02_Topics/Agent_PostTraining", "# Agent PostTraining\n\n智能体后训练专题")

    # LLM Topics
    llm_topics = [
        "RLHF 总览", "DPO 与 Preference Optimization", "GRPO 与 Reasoning RL",
        "Reward Model", "Process Reward Model", "Test-Time Scaling",
        "Data Quality in Post-training"
    ]
    for t in llm_topics:
        create_doc(notebook_id, f"/02_Topics/LLM_PostTraining/{t}", topic_template.format(name=t))

    # VLM Topics
    vlm_topics = [
        "Visual Instruction Tuning", "Multimodal Preference Optimization",
        "VLM Alignment", "Multimodal Reasoning", "Video-LMM Post-training"
    ]
    for t in vlm_topics:
        create_doc(notebook_id, f"/02_Topics/VLM_PostTraining/{t}", topic_template.format(name=t))

    # Agent Topics
    agent_topics = [
        "Tool-use RL", "Agent Reward Design", "Multi-agent Post-training"
    ]
    for t in agent_topics:
        create_doc(notebook_id, f"/02_Topics/Agent_PostTraining/{t}", topic_template.format(name=t))

    create_doc(notebook_id, "/02_Topics/Evaluation", topic_template.format(name="Evaluation"))

    # 5. 03_Methods Pages
    method_template = """# {name}

## 方法定义

## 它解决什么问题？

## 方法本质

## 关键公式或机制

## 适用场景

## 局限性

## 和相关方法的区别

## 代表论文

## 来自论文阅读的思考
> 这里沉淀跨论文的个人理解。

## 我自己的判断

## 可分享观点

## 相关页面

---
*回到主入口: [[总入口]]*"""

    methods = [
        "SFT", "RLHF", "DPO", "GRPO", "Reward_Modeling",
        "Process_Reward_Model", "Verifier_Critic", "Test_Time_Scaling", "Multimodal_Alignment"
    ]
    for m in methods:
        create_doc(notebook_id, f"/03_Methods/{m}", method_template.format(name=m))

    # 6. 04_Problems Pages
    problem_template = """# {name}

## 问题定义

## 为什么这个问题重要？

## 它在 LLM/VLM post-training 中如何出现？

## 典型表现

## 相关方法

## 代表论文

## 来自论文阅读的思考
> 这里记录我对这个问题的长期理解。

## 我自己的判断

## 可分享观点

## 相关页面

---
*回到主入口: [[总入口]]*"""

    problems = [
        "Reward_Hacking", "Length_Bias", "Credit_Assignment", "Distribution_Shift",
        "Reward_Model_Overfitting", "Evaluation_Leakage", "Multimodal_Hallucination",
        "Visual_Grounding_Failure", "Tool_Use_Credit_Assignment", "Test_Time_Compute_Cost",
        "Data_Quality"
    ]
    for p in problems:
        create_doc(notebook_id, f"/04_Problems/{p}", problem_template.format(name=p))

    # 7. 05_Share Pages
    create_doc(notebook_id, "/05_Share/Weekly_Reports", "# Weekly Reports\n\n周报索引页。")
    create_doc(notebook_id, "/05_Share/Group_Meeting", "# Group Meeting\n\n组会分享材料目录。")
    create_doc(notebook_id, "/05_Share/Blog_Drafts", "# Blog Drafts\n\n技术博客草稿。")
    create_doc(notebook_id, "/05_Share/PPT_Outlines", "# PPT Outlines\n\n汇报与分享 PPT 大纲。")
    create_doc(notebook_id, "/05_Share/Share_Topic_Pool", "# Share Topic Pool\n\n待分享选题候选池。")

    share_template_md = """# 分享标题

## Share Metadata
<!-- START_AUTO_METADATA -->
- **Share Status**: Draft / Ready / Presented / Archived
- **Target Audience**: 
- **Target Duration**: 5min / 15min / 30min
- **Related Papers**: 
- **Related Methods**: 
- **Related Problems**: 
- **Last Updated**: 
<!-- END_AUTO_METADATA -->

## 观点来源
<!-- START_SOURCES -->
- 
<!-- END_SOURCES -->

## 论文来源
- 

## 方法页来源
- 

## 问题页来源
- 

## 内部链接来源
- 

## 我的核心判断
- 

## 5 分钟分享结构
1. **背景问题**：
2. **核心矛盾**：
3. **方法思想**：
4. **实验结论**：
5. **我的评价**：

## 15 分钟分享结构
1. **为什么读这篇论文/主题**：
2. **相关方法背景**：
3. **核心问题定义**：
4. **方法细节**：
5. **实验与 ablation**：
6. **创新性评价**：
7. **局限与讨论**：
8. **和 LLM/VLM post-training 主线的关系**：

## 可讨论问题
1. 
2. 

## 后续可扩展成 PPT 的部分
- 
"""
    create_doc(notebook_id, "/05_Share/Group_Meeting/分享稿模板", share_template_md)
    create_doc(notebook_id, "/05_Share/Group_Meeting/DPO为什么没有完全替代RLHF", share_template_md.replace("分享标题", "DPO为什么没有完全替代RLHF"))
    create_doc(notebook_id, "/05_Share/Group_Meeting/GRPO的核心思想与潜在问题", share_template_md.replace("分享标题", "GRPO的核心思想与潜在问题"))
    create_doc(notebook_id, "/05_Share/Group_Meeting/VLM后训练到底难在哪里", share_template_md.replace("分享标题", "VLM后训练到底难在哪里"))

    # 8. 06_Workflows Pages
    create_doc(notebook_id, "/06_Workflows/Prompts", "# Prompts\n\n论文处理核心系统提示词库。")
    create_doc(notebook_id, "/06_Workflows/Reading_Workflows", "# Reading Workflows\n\n阅读工作流规程。")
    create_doc(notebook_id, "/06_Workflows/Automation", "# Automation\n\n自动化同步脚本说明。")

    # Workflow prompts
    create_doc(notebook_id, "/06_Workflows/Prompts/论文快速筛选助手 Prompt", "# 论文快速筛选助手 Prompt (Skimmer Verdict)\n\n**用途**：输入摘要和 Introduction，由 AI 评估论文的动机、贡献与技术类型，输出精读建议级别（High/Medium/Low）。")
    create_doc(notebook_id, "/06_Workflows/Prompts/论文精读助手 Prompt", "# 论文精读助手 Prompt (AI Draft Generator)\n\n**用途**：在决定精读后，辅助提取核心内容、关键数学公式、消融实验结论，生成 AI Draft Summary 草稿。")
    create_doc(notebook_id, "/06_Workflows/Prompts/论文批判性复盘 Prompt", "# 论文批判性复盘 Prompt (Critical Examiner)\n\n**用途**：寻找论文的方法盲点、实验设计漏洞及可能被忽视的计算开销，辅助填写 My Judgment。")
    create_doc(notebook_id, "/06_Workflows/Prompts/论文分享生成 Prompt", "# 论文分享生成 Prompt (Storyline Planner)\n\n**用途**：根据人工精读笔记和批判评价，自动梳理适合学术报告或组会的 Slides 大纲。")

    # Reading Workflows
    create_doc(notebook_id, "/06_Workflows/Reading_Workflows/LLM VLM Post-training 论文阅读流程", "# LLM VLM Post-training 论文阅读流程\n\n**流程简述**：通过抓取工具生成队列 ➔ 使用 Skimmer 粗筛 ➔ 中低优先级丢归档/高优先级进精读队列 ➔ 填写精读卡片 ➔ 提炼回流 ➔ 分享输出。")
    
    reading_thoughts_flow_md = """# 阅读后思考沉淀流程

为了防止笔记成为“论文坟场”，请严格按照以下步骤完成阅读和思考沉淀：

1. **精选阅读**：从[[精选阅读队列]]中挑选需要深读的论文；
2. **打开卡片**：在 `01_Papers` 下找到对应的论文卡片；
3. **精读论文**：阅读论文全文或核心章节；
4. **记精读笔记**：在卡片的 `My Reading Notes` 区域记录推导过程、关键公式或架构理解；
5. **写批判判断**：在卡片的 `My Judgment` 区域记录论文局限性、真实贡献与评价；
6. **做 AI 审查**：在卡片的 `AI Draft Review` 标记 AI 生成的草稿是否可信，并记录错误；
7. **知识提取**：在 `Knowledge Extraction` 关联到对应的 Topic、Method、Problem 页面；
8. **更新回流状态**：勾选卡片上的 `Knowledge Backfeed Status`；
9. **信息上游回流**：打开关联的 Topic/Method/Problem 页面，在 **[来自论文阅读的思考]** 分区中追加你的对比思考；
10. **登记思考索引**：打开[[阅读后思考索引]]，登记核心判断，判断是否值得在 `05_Share` 启动分享稿。
"""
    create_doc(notebook_id, "/06_Workflows/Reading_Workflows/阅读后思考沉淀流程", reading_thoughts_flow_md)

    # Automation Workflows
    create_doc(notebook_id, "/06_Workflows/Automation/PostTrain Radar 使用流程", "# PostTrain Radar 使用流程\n\n说明如何调用本项目的抓取与分类流程。")
    create_doc(notebook_id, "/06_Workflows/Automation/思源同步流程", "# 思源同步流程\n\n介绍运行 `run_pipeline.py` 进行选择性同步的具体命令与参数配置。")
    
    sync_policy_md = """# 精选同步原则

为了保持思源工作台的整洁 and 专注度，请项目侧和人工严格遵守以下同步原则：

1. **思源不是全量论文仓库**：全量爬取和分类数据仅在 SQLite 数据库、本地 CSV 报告和 Markdown report 中留存。
2. **精选同步**：思源只同步 `selected`（人工勾选 `include_in_siyuan: true`）、`high` 优先级、`core` post-training 以及 `worth_sharing` 论文。
3. **数量限制**：对于大型会议目录，默认最多同步约 **30** 篇论文卡片，超过则根据优先级和置信度截断，避免卡片堆积污染工作台。
4. **过滤低相关**：`Low` 优先级或未分类为相关（`is_relevant = 0`）的论文绝对禁止同步到思源中。
5. **精选生成**：Share Brief 和 Knowledge Patch 仅为精选同步的论文生成，不进行全量生成。
6. **归档非删除**：如果自动同步了过多无用论文卡片，请使用清理脚本将其归档到 `99_Archive/Bulk_Imported`，保留已有人工笔记的卡片，禁止直接暴力删除。
7. **人工笔记保护**：清理和同步工具必须无条件保护 `My Reading Notes`、`My Judgment`、`AI Draft Review` 非空的页面。
"""
    create_doc(notebook_id, "/06_Workflows/Automation/精选同步原则", sync_policy_md)

    safety_rules_md = """# 安全同步规则

为了避免自动工具破坏或覆盖人工编辑的高价值研究心得，系统底层 Exporter 必须遵循以下安全规则：

1. **可自动更新/覆盖的区域**：
   - `Auto Metadata` (自动元数据，例如状态、会议变化)
   - `AI Draft Summary` (AI 总结区)
   - `Knowledge Extraction` (提取到的关联页)
   - `Share Decision` (分享决策模板)
   - `Next Action` (下一步行动)
2. **绝对禁止覆盖的区域**：
   - `My Reading Notes` (人工阅读记录)
   - `My Judgment` (人工思考与批判性判断)
   - `AI Draft Review` (人工对 AI 草稿的审查)
3. **保留不重置**：
   - `Knowledge Backfeed Status` (回流勾选框状态)
4. **覆盖拒绝与保护**：
   - 即使传入 `--overwrite` 参数，同步工具也必须提取旧笔记中的这三大保护区域内容并进行安全合并。
   - 任何自动工具在任何模式下均绝对禁止直接删除、清空或覆盖这三个保护分区。
   - 人工记录的清除和删除只能在思源 GUI 中由用户手动执行。
"""
    create_doc(notebook_id, "/06_Workflows/Automation/安全同步规则", safety_rules_md)

    # 9. 99_Archive Pages
    create_doc(notebook_id, "/99_Archive/Bulk_Imported", "# Bulk Imported\n\n存放通过清理工具移入的、未读或未被精选的大批量导入卡片。")
    create_doc(notebook_id, "/99_Archive/Deprecated_Templates", "# Deprecated Templates\n\n历史废弃笔记模板。")
    create_doc(notebook_id, "/99_Archive/Old_Share_Drafts", "# Old Share Drafts\n\n历史已分享完毕或废弃的组会分享、博客草稿。")
    create_doc(notebook_id, "/99_Archive/False_Positive_Papers", "# False Positive Papers\n\n误筛选为相关的论文，移至此处以归档并避免干扰主知识库。")

    print("\n=== SiYuan Workspace Rebuild Completed Successfully ===")

if __name__ == "__main__":
    main()
