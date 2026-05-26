import requests
import json
import time
import argparse

API_URL = "http://127.0.0.1:6806"
API_TOKEN = "bqrrmb48o36gbpo2"
NOTEBOOK_NAME = "PostTrain_Radar"
OVERWRITE = False

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

def find_doc(notebook_id, target_path_without_ext):
    components = target_path_without_ext.strip("/").split("/")
    if not components:
        return None
    
    current_path = "/"
    current_id = None
    
    for comp in components:
        res = call_api("/api/filetree/listDocsByPath", {
            "notebook": notebook_id,
            "path": current_path
        })
        if not res or res.get("code") != 0:
            return None
            
        files = res.get("data", {}).get("files", [])
        found = False
        for f in files:
            name = f.get("name", "")
            if name.endswith(".sy"):
                name = name[:-3]
            if name == comp:
                current_id = f.get("id")
                current_path = f.get("path")
                if current_path.endswith(".sy"):
                    current_path = current_path[:-3]
                found = True
                break
        if not found:
            return None
            
    return current_id

def create_doc(notebook_id, path, md_content=""):
    doc_id = find_doc(notebook_id, path)
    if doc_id:
        if not OVERWRITE:
            print(f"[-] Doc {path} already exists. Skipping (overwrite=False).")
            return doc_id
        else:
            print(f"[*] Updating doc in place: {path} (ID: {doc_id})...")
            update_res = call_api("/api/block/updateBlock", {
                "id": doc_id,
                "dataType": "markdown",
                "data": md_content
            })
            if update_res and update_res.get("code") == 0:
                print(f"  [+] Success updating block")
                return doc_id
            else:
                print(f"  [!] Failed updating: {update_res}")
                return doc_id

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
    global OVERWRITE
    parser = argparse.ArgumentParser(description="Initialize or update SiYuan workspace structure.")
    parser.add_argument("--overwrite", action="store_true", help="Force overwrite existing documents (updating them in place)")
    args = parser.parse_args()
    OVERWRITE = args.overwrite

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
| Metadata Key | Value |
| :--- | :--- |
| Venue |  |
| Year |  |
| Authors |  |
| Source |  |
| Status |  |
| Data Origin |  |
| Type |  |
| Tags |  |
| Priority |  |
| Relevance Level |  |
| Confidence |  |
| Reason |  |
| Method Tags |  |
| Problem Tags |  |
| Core Post-Training |  |
| URL |  |
| PDF |  |

## AI Draft Summary
*   **一句话总结**: 作者认为 ______，因此提出 ______。
*   **解决的问题**: 待精读后补充
*   **核心方法**: 
*   **实验结论**: 

## Classification Evidence
| Section | Keyword Group | Title Matches | Abstract Matches | Evidence Detail |
| :--- | :--- | :--- | :--- | :--- |
| - | - | - | - | No classification evidence recorded. |

## AI Draft Review
> 说明：人工对 AI 生成草稿的审查记录，自动更新不会覆盖。
*   **AI Draft 是否可信**: High / Medium / Low
*   **错误点**: 
*   **我修正后的理解**: 
*   **是否需要重新生成**: 

## My Reading Notes
> 说明：这里是人工精读笔记区，任何自动同步均不会覆盖此区。
*   **阅读时间**: 
*   **精读笔记**: 
    *   (在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)

## My Judgment
> 说明：这里是人工独立技术判断区，任何自动同步均不会覆盖此区。
*   **论文盲点/局限性**: 
*   **实验设计局限**: 
*   **我的评价**: 
    *   (在这里写下您对该文的真实技术评价，是否真正解决了痛点？)

## Knowledge Extraction
*   **可提炼的方法/技术路线**: ➔ 待人工补充
*   **可引入的问题意识/技术冲突**: ➔ 待人工补充
*   **有启发的后续实验设计**: 

## Knowledge Backfeed Status
*   [ ] 已回流 Topic 页面
*   [ ] 已回流 Method 页面
*   [ ] 已回流 Problem 页面
*   [ ] 已加入 Share 候选池
*   [ ] 已更新 阅读后思考索引

## Share Decision
*   **是否值得分享**: 是/否
*   **分享主题建议**: 
*   **分享目标受众**: 

## Next Action
*   [ ] 读 Introduction
*   [ ] 读 Method
*   [ ] 读 Experiments
*   [ ] 看 Ablation
*   [ ] 找相关论文对比
*   [ ] 回流到知识页
*   [ ] 判断是否生成分享稿

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
    
    # 05_Share/Group_Meeting/Paper_Briefs directories
    create_doc(notebook_id, "/05_Share/Group_Meeting/Paper_Briefs", "# Paper Briefs\n\n单篇论文组会分享稿。")
    create_doc(notebook_id, "/05_Share/Group_Meeting/Paper_Briefs/ICLR_2025", "# ICLR 2025 Paper Briefs")
    create_doc(notebook_id, "/05_Share/Group_Meeting/Paper_Briefs/NeurIPS_2025", "# NeurIPS 2025 Paper Briefs")
    create_doc(notebook_id, "/05_Share/Group_Meeting/Paper_Briefs/ICML_2025", "# ICML 2025 Paper Briefs")
    create_doc(notebook_id, "/05_Share/Group_Meeting/Paper_Briefs/ACL_2025", "# ACL 2025 Paper Briefs")
    create_doc(notebook_id, "/05_Share/Group_Meeting/Paper_Briefs/EMNLP_2025", "# EMNLP 2025 Paper Briefs")
    create_doc(notebook_id, "/05_Share/Group_Meeting/Paper_Briefs/CVPR_2025", "# CVPR 2025 Paper Briefs")
    create_doc(notebook_id, "/05_Share/Group_Meeting/Paper_Briefs/ICCV_2025", "# ICCV 2025 Paper Briefs")
    create_doc(notebook_id, "/05_Share/Group_Meeting/Paper_Briefs/ArXiv_Preprints", "# ArXiv Preprints Paper Briefs")
    create_doc(notebook_id, "/05_Share/Group_Meeting/Paper_Briefs/Manual_Import", "# Manual Import Paper Briefs")

    share_template_md = """# 分享标题

## Share Metadata
- **Share Status**: Draft / Ready / Presented / Archived
- **Target Audience**: 
- **Target Duration**: 5min / 15min / 30min
- **Related Papers**: 
- **Related Methods**: 
- **Related Problems**: 
- **Last Updated**: 

## 观点来源
- 

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

    # 10. PostTrain Radar 完整工作流
    workflow_md = """# PostTrain Radar 完整工作流

> PostTrain Radar 不是全量论文收藏库，而是一个面向 LLM/VLM post-training 论文的“筛选—阅读—沉淀—分享”研究工作流。

核心原则：

```text
项目负责全量抓取和初筛；
思源只保存精选论文；
阅读 session 辅助理解和批判；
我负责最终判断、笔记和分享。
```

---

## 1. 系统定位

PostTrain Radar 的目标不是把所有论文都塞进思源，而是帮助我完成：

```text
顶会论文搜集
→ LLM/VLM post-training 相关论文筛选
→ 精选论文进入思源
→ 人工阅读和判断
→ 知识回流到方法页 / 问题页
→ 形成组会分享、博客或 PPT 大纲
```

思源知识库的定位是：

```text
精选阅读工作台
个人思考沉淀区
专题分享准备区
```

不是：

```text
ICLR / NeurIPS / ACL / CVPR 全量论文数据库
```

全量数据保存在：

```text
SQLite 数据库
CSV / Markdown reports
data/processed/
data/reports/
data/00_Index/
```

精选内容才进入思源。

---

## 2. 三个固定 session 分工

### 2.1 PostTrain Radar 项目 session

负责工程 and 自动化：

```text
论文抓取
分类打标
生成候选列表
生成 Paper Card
同步思源
导出 reading packet
清理 / 归档
GitHub / 测试 / bug 修复
```

适合问它：

```text
pipeline 为什么报错？
候选列表怎么生成？
为什么某篇论文没同步？
Paper Card 格式是否正确？
cleanup_siyuan 怎么用？
```

---

### 2.2 思源知识库设计 session

负责结构 and 规范：

```text
知识库目录结构
Paper Card 模板
Topic / Method / Problem 页面模板
分享页模板
同步安全规则
精选同步原则
阅读后思考沉淀流程
```

适合问它：

```text
知识库结构是否合理？
某个页面该放在哪里？
Paper Card 模板是否需要改？
方法页和问题页怎么组织？
```

---

### 2.3 论文阅读 session

负责选定论文后的学术阅读：

```text
审查自动分类
分析研究问题
解释方法本质
判断创新点
批判实验逻辑
生成 My Reading Notes 草稿
生成 My Judgment 草稿
建议知识回流页面
生成 5min / 15min 分享稿
```

适合问它：

```text
这篇论文到底解决什么问题？
它的核心创新是否实质？
实验是否支撑 claim？
应该回流到哪个 Method / Problem 页面？
是否值得分享？
```

---

## 3. 知识库目录结构

```text
PostTrain Radar
├── 00_Index
│   ├── 总入口
│   ├── LLM Post-training 路线图
│   ├── VLM Post-training 路线图
│   ├── 精选阅读队列
│   ├── 阅读后思考索引
│   ├── 知识回流建议
│   └── 已分享内容索引
│
├── 01_Papers
│   ├── Paper_Card_Template
│   ├── ICLR_2025
│   ├── NeurIPS_2025
│   ├── ICML_2025
│   ├── ACL_2025
│   ├── EMNLP_2025
│   ├── CVPR_2025
│   ├── ICCV_2025
│   ├── ArXiv_Preprints
│   └── Manual_Import
│
├── 02_Topics
│   ├── LLM_PostTraining
│   ├── VLM_PostTraining
│   ├── Agent_PostTraining
│   └── Evaluation
│
├── 03_Methods
│   ├── SFT
│   ├── RLHF
│   ├── DPO
│   ├── GRPO
│   ├── Reward_Modeling
│   ├── Process_Reward_Model
│   ├── Verifier_Critic
│   ├── Test_Time_Scaling
│   └── Multimodal_Alignment
│
├── 04_Problems
│   ├── Reward_Hacking
│   ├── Length_Bias
│   ├── Credit_Assignment
│   ├── Distribution_Shift
│   ├── Reward_Model_Overfitting
│   ├── Evaluation_Leakage
│   ├── Multimodal_Hallucination
│   ├── Visual_Grounding_Failure
│   ├── Tool_Use_Credit_Assignment
│   ├── Test_Time_Compute_Cost
│   └── Data_Quality
│
├── 05_Share
│   ├── Group_Meeting
│   │   ├── Paper_Briefs
│   │   ├── 分享稿模板
│   │   ├── DPO为什么没有完全替代RLHF
│   │   ├── GRPO的核心思想与潜在问题
│   │   └── VLM后训练到底难在哪里
│   ├── Weekly_Reports
│   ├── Blog_Drafts
│   ├── PPT_Outlines
│   └── Share_Topic_Pool
│
├── 06_Workflows
│   ├── Prompts
│   ├── Reading_Workflows
│   └── Automation
│
└── 99_Archive
    ├── Bulk_Imported
    ├── Deprecated_Templates
    ├── Old_Share_Drafts
    └── False_Positive_Papers
```

---

## 4. 标准使用流程

### Step 1：全量抓取与分类

由 PostTrain Radar 项目完成。

示例：

```bash
./venv/bin/python run_pipeline.py \
  --venue ICLR \
  --year 2025 \
  --sync-target markdown
```

这一步只生成本地数据，不同步思源。

主要输出：

```text
data/processed/
data/reports/
data/00_Index/Reading_Queue_Full.md
data/00_Index/精选阅读队列.md
```

注意：

```text
Reading_Queue_Full 只保存在本地，不进入思源。
```

---

### Step 2：生成候选论文列表

```bash
./venv/bin/python scripts/generate_override_candidates.py \
  --venue ICLR \
  --year 2025 \
  --top-k 50
```

输出：

```text
data/manual/tag_overrides_candidates_iclr_2025.yaml
```

这个文件用于人工挑选论文。

每篇论文会包含：

```text
title
source_id
venue
year
relevance_level
priority
confidence
model_type
method_tags
problem_tags
matched_evidence
reviewer_comment
```

所有同步开关默认是 false：

```yaml
manual_selected: false
include_in_siyuan: false
include_in_reading_queue: false
include_in_knowledge_patches: false
include_in_share_pool: false
```

---

### Step 3：人工选择论文

打开：

```text
data/manual/tag_overrides_candidates_iclr_2025.yaml
```

选择我真正想读的论文，将其复制到：

```text
data/manual/tag_overrides.yaml
```

并改成：

```yaml
manual_selected: true
include_in_siyuan: true
include_in_reading_queue: true
```

如果觉得它适合分享，可以加：

```yaml
include_in_share_pool: true
share_status: "WorthSharing"
```

如果只是暂时想读，不一定分享：

```yaml
share_status: "Maybe"
```

推荐每个大型会议只选：

```text
5–10 篇精读候选
最多不超过 30 篇进入思源
```

---

### Step 4：selected dry-run

在真正同步前，必须先 dry-run：

```bash
./venv/bin/python run_pipeline.py \
  --venue ICLR \
  --year 2025 \
  --sync-target siyuan \
  --siyuan-scope selected \
  --max-siyuan-notes 30 \
  --dry-run
```

检查输出：

```text
data/reports/siyuan_sync_plan_iclr_2025.md
```

确认：

```text
只同步 selected 论文；
不会同步 Reading_Queue_Full；
不会同步几百篇论文；
不会覆盖 Prompt 页面；
不会批量生成无用 Share Brief。
```

---

### Step 5：selected 真同步

确认 dry-run 没问题后执行：

```bash
./venv/bin/python run_pipeline.py \
  --venue ICLR \
  --year 2025 \
  --sync-target siyuan \
  --siyuan-scope selected \
  --max-siyuan-notes 30
```

同步到思源的内容包括：

```text
精选阅读队列
阅读后思考索引
知识回流建议
分享候选池
selected 论文卡片
必要的 workflow / prompt 页面
```

不会同步：

```text
Reading_Queue_Full
全量 relevant papers
Low priority 未精选论文
未选中的 per-paper Share Brief
```

---

## 5. Paper Card 使用方式

每篇进入思源的论文卡片包含：

```text
Auto Metadata
AI Draft Summary
Classification Evidence
AI Draft Review
My Reading Notes
My Judgment
Knowledge Extraction
Knowledge Backfeed Status
Share Decision
Next Action
```

---

### 5.1 自动生成区域

由 PostTrain Radar 生成：

```text
Auto Metadata
AI Draft Summary
Classification Evidence
```

这些内容用于快速判断论文是否值得读。

---

### 5.2 人工保护区域

这些区域任何自动同步都不能覆盖：

```text
AI Draft Review
My Reading Notes
My Judgment
Knowledge Backfeed Status
```

其中最重要的是：

```text
My Reading Notes
My Judgment
```

这两个区域必须以我的理解为准，不能直接照抄 AI。

---

### 5.3 知识回流区域

```text
Knowledge Extraction
Knowledge Backfeed Status
```

用于判断这篇论文应该回流到：

```text
02_Topics
03_Methods
04_Problems
05_Share
```

---

## 6. 导出 reading packet

选定论文后，导出阅读包：

```bash
./venv/bin/python scripts/export_reading_packet.py \
  --title "论文标题" \
  --venue ICLR \
  --year 2025
```

输出：

```text
data/reading_packets/{safe_title}_reading_packet.md
```

reading packet 应包含：

```text
Paper Card
Auto Metadata
AI Draft Summary
Classification Evidence
Abstract
method_tags
problem_tags
relevance_level
priority
推荐回流页面
Share Brief 开发草稿
阅读助手使用说明
```

---

## 7. 开启论文阅读 session

新开一个专门的阅读 session。

开场输入：

```text
下面是 PostTrain Radar 生成的 reading packet。请你作为我的 PostTrain Radar 论文阅读助手，基于这个 packet 审查自动分类是否合理，并帮助我生成适合写入思源 Paper Card 的 My Reading Notes、My Judgment、AI Draft Review、Knowledge Extraction、Share Decision 和 Next Action。

注意：不要脱离 PostTrain Radar 泛泛总结论文。请围绕 Paper Card、Classification Evidence、Method Tags、Problem Tags、知识回流和分享输出进行分析。
```

然后粘贴 reading packet。

---

## 8. 阅读 session 的任务

阅读 session 需要帮助我完成：

```text
审查自动分类是否合理；
分析论文核心问题；
判断方法本质；
评价创新点；
批判实验逻辑；
指出局限性；
生成 My Reading Notes 草稿；
生成 My Judgment 草稿；
建议 Knowledge Extraction；
判断 Share Decision；
生成分享稿结构。
```

但最终写入思源前，我必须人工确认。

---

## 9. 我如何填 Paper Card

### My Reading Notes

写：

```text
我为什么读这篇论文；
读完后真正理解了什么；
关键方法或机制；
实验细节；
还没看懂的地方。
```

---

### My Judgment

写：

```text
这篇论文的真实贡献；
它是否只是 benchmark / 工程组合；
它和 SFT / RLHF / DPO / GRPO / Reward Model 的关系；
我的批判性评价。
```

---

### AI Draft Review

写：

```text
AI Draft 是否可信；
AI 错在哪里；
我修正后的理解；
是否需要重新生成。
```

---

### Knowledge Extraction

写：

```text
应该回流到哪些 Topic 页面；
应该回流到哪些 Method 页面；
应该回流到哪些 Problem 页面；
是否应该进入 Share。
```

注意：

```text
不要写无意义占位双链。
不要写 [[方法或机制链接]]。
不确定就写“待人工补充”。
```

---

### Share Decision

写：

```text
是否值得分享；
分享价值；
适合 5min / 15min / 30min；
分享角度；
目标听众。
```

---

## 10. 知识回流流程

读完论文后，不应该只停留在 Paper Card。

需要把有价值的观点回流到：

```text
03_Methods
04_Problems
05_Share
```

---

### 10.1 回流到 Method 页面

例如：

```text
[[Reward_Modeling]]
[[DPO]]
[[GRPO]]
[[RLHF]]
[[Test_Time_Scaling]]
```

写入：

```text
## 来自论文阅读的思考
```

内容应该是跨论文可复用的理解，而不是单篇摘要。

---

### 10.2 回流到 Problem 页面

例如：

```text
[[Reward_Hacking]]
[[Length_Bias]]
[[Credit_Assignment]]
[[Evaluation_Leakage]]
[[Distribution_Shift]]
[[Reward_Model_Overfitting]]
```

写入：

```text
## 来自论文阅读的思考
```

内容应该是问题意识、风险、矛盾或局限。

---

### 10.3 回流到 Share 页面

如果论文值得分享，进入：

```text
05_Share/Group_Meeting/Paper_Briefs/{VENUE}_{YEAR}/
```

或者整理成专题分享：

```text
05_Share/Group_Meeting/
```

分享稿必须包含：

```text
观点来源
论文来源
方法页来源
问题页来源
内部链接来源
我的核心判断
5 分钟分享结构
15 分钟分享结构
可讨论问题
```

---

## 11. 分享输出流程

如果一篇论文值得分享，先让阅读 session 生成：

```text
30 秒口头概括
5 分钟组会分享结构
15 分钟技术分享结构
3 个讨论问题
```

然后我再根据需要改成：

```text
组会分享稿
博客草稿
PPT 大纲
```

---

## 12. 清理与归档规则

如果思源中误同步了太多论文，不直接删除，优先归档：

```bash
./venv/bin/python scripts/cleanup_siyuan.py \
  --venue ICLR \
  --year 2025 \
  --mode archive \
  --keep-scope selected \
  --dry-run
```

确认后再执行真实归档：

```bash
./venv/bin/python scripts/cleanup_siyuan.py \
  --venue ICLR \
  --year 2025 \
  --mode archive \
  --keep-scope selected \
  --no-dry-run
```

规则：

```text
默认 dry-run；
默认 archive；
delete 必须强确认；
含 My Reading Notes / My Judgment / AI Draft Review 的页面不能清理；
归档使用 moveDocsByID，不能删除重建。
```

---

## 13. 禁止操作

日常不要运行：

```bash
--siyuan-scope all
```

除非非常确定，并且必须显式：

```bash
--confirm-all-sync
```

日常也不要把：

```text
Reading_Queue_Full
全量 candidates
全量 relevant papers
Low priority 未精选论文
```

同步进思源。

---

## 14. 每篇论文的处理等级

### A 档：精读

适合：

```text
Reward Model
DPO
GRPO
RLHF
VLM Alignment
和分享强相关
和我的研究方向有关
```

需要完整填写：

```text
My Reading Notes
My Judgment
AI Draft Review
Knowledge Extraction
Share Decision
```

---

### B 档：泛读

只记录：

```text
一句话理解
为什么不精读
是否以后回看
```

---

### C 档：跳过

保留在本地数据库，不进入思源。

---

## 15. 验收标准

这个工作流是否成功，不看同步了多少论文，而看是否完成下面闭环：

```text
我能从候选列表中快速选出 5–10 篇；
思源中只出现少量精选论文；
Paper Card 阅读体验干净；
My Reading Notes 不会被覆盖；
我能读完一篇并写出 My Judgment；
我能把一个观点回流到 Method / Problem 页面；
我能基于它生成 5 分钟分享稿。
```

---

## 16. 当前推荐的第一篇闭环论文

建议优先测试：

```text
How to Evaluate Reward Models for RLHF
```

原因：

```text
方向明确：Reward Model / RLHF / Evaluation；
适合回流到 Reward_Modeling；
适合讨论 Evaluation_Leakage / Reward_Hacking；
适合做 5 分钟组会分享；
能验证整个阅读闭环。
```

---

# 最终工作流总结

```text
PostTrain Radar 项目：
全量抓取、分类、候选、同步、导出 reading packet

思源知识库：
保存精选论文、人工笔记、知识回流、分享材料

阅读 session：
陪我读论文、批判分析、生成草稿、辅助分享

我自己：
选择论文、阅读正文、确认判断、写入最终笔记、做分享
```

最终目标不是“收集很多论文”，而是：

```text
少量精选论文
→ 深入理解
→ 形成自己的判断
→ 沉淀到知识库
→ 输出为分享
```
"""
    create_doc(notebook_id, "/完整工作流", workflow_md)

    print("\n=== SiYuan Workspace Rebuild Completed Successfully ===")

if __name__ == "__main__":
    main()
