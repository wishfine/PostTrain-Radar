# 🧭 PostTrain Radar

A top-conference paper tracking and taxonomy system for LLM/VLM post-training research.

---

## 1. 项目简介 (Introduction)

**PostTrain Radar** 是一个面向学术研究者与大模型全栈工程师的前沿论文追踪、筛选、分类与分享辅助系统。它专门用于自动搜集顶级人工智能会议（ICLR, NeurIPS, ICML, ACL, CVPR 等）的论文，自动筛选出与 **LLM/VLM 后训练 (Post-Training) / 对齐 (Alignment) / 推理强化学习 (Reasoning RL)** 相关的论文，并辅助生成结构化的阅读笔记与分享报告，深度融合个人知识库。

## 2. 为什么做这个项目 (Motivation)

在 LLM/VLM 领域，后训练（SFT、RLHF、DPO、GRPO、推理期缩放等）的研究日新月异，顶级会议上涌现出海量论文。人工逐一筛选成本极高，而普通的通用论文爬虫又无法精确聚焦在 Post-Training 这个垂直方向。

**PostTrain Radar** 旨在解决这些痛点：
- **高效去噪**：自动将海量会议论文元数据过滤，只留下高度相关的后训练候选工作。
- **结构分类**：基于方法、模型和问题痛点进行规则/启发式分类，建立立体知识地图。
- **无缝对接笔记软件**：自动为每一篇论文生成包含“防覆盖保护”的阅读笔记和组会分享稿，并自动同步至思源笔记或 Obsidian，形成闭环工作流。

## 3. 项目定位说明 (Positioning)

> [!IMPORTANT]
> **PostTrain Radar 不是为了替代人工读论文！**
> 本系统的核心价值在于帮助研究者从大量顶会论文中**快速定位**值得深读的 LLM/VLM post-training 工作，自动做好信息归档和模板填充，为后续**人工阅读、批判性分析和技术分享**提供强有力的结构化辅助。

---

## 4. 支持的数据源与会议 (Data Sources & Venues)

### 数据源 (v0.1)
- **OpenReview (API v2)**：第一版完整实现（针对已接受论文进行高召回抓取，并在断网/限频时提供高保真本地 fallback 数据）。
- **ACL Anthology / CVF Open Access**：预留接口和骨架 Stub，后续逐步完善。

### 会议与年份 (Conferences)
- **ICLR** (2025+ 完整支持)
- **NeurIPS / ICML** (预留结构)
- **ACL / EMNLP / NAACL** (预留结构)
- **CVPR / ICCV / ECCV** (预留结构)

---

## 5. 支持的分类标签体系 (Taxonomy & Tags)

分类器将候选论文归类为以下维度：

1. **模型类型 (`model_type`)**：`LLM` | `VLM` | `Video-LMM` | `Agent` | `Reward Model` | `Other`
2. **后训练方法 (`post_training_types`)**：
   - `SFT / Instruction Tuning` | `RLHF / PPO` | `RLAIF` | `DPO / Preference Optimization`
   - `GRPO / Reasoning RL` | `Reward Modeling` | `Process Reward Model` | `Outcome Reward Model`
   - `Verifier / Critic` | `Test-Time Scaling` | `Self-Improvement` | `Multimodal Alignment`
   - `Visual Instruction Tuning` | `Safety Alignment` | `Data Selection / Data Quality` | `Evaluation / Benchmark`
3. **常见痛点/问题标签 (`problem_tags`)**：
   - `Reward Hacking` | `Length Bias` | `Credit Assignment` | `Preference Data Distribution Shift`
   - `Reward Model Overfitting` | `Evaluation Leakage` | `Multimodal Hallucination` | `Visual Grounding Failure`
   - `Tool-use Credit Assignment` | `Test-time Compute Cost` | `Data Quality`

---

## 6. 安装方式 (Installation)

本项目运行在 Python 3.10+ 环境下。推荐使用虚拟环境进行安装以避免环境污染：

```bash
# 1. 克隆/进入项目目录
cd PostTrain_Radar

# 2. 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate  # macOS / Linux

# 3. 安装依赖项
pip install -r requirements.txt
```

---

## 7. 使用示例 (Usage Examples)

### 一键运行全链路 (Recommended)
使用 `run_pipeline.py` 一键完成收集、粗筛、分类、报告生成和笔记同步：

```bash
# 同步至本地 Markdown 目录
python run_pipeline.py --venue ICLR --year 2025 --sync-target markdown

# 同步至思源笔记 (需设置环境变量 SIYUAN_TOKEN)
export SIYUAN_TOKEN="your_siyuan_api_token"
python run_pipeline.py --venue ICLR --year 2025 --sync-target siyuan

# 同步至思源笔记并强制更新 (合并并保留人工手写部分)
python run_pipeline.py --venue ICLR --year 2025 --sync-target siyuan --overwrite
```

### 组件分步执行 (Granular CLI)
如果你需要分步控制，可以按以下顺序运行脚本：

```bash
# 1. 抓取论文并生成 papers.csv
python scripts/collect_openreview.py --venue ICLR --year 2025

# 2. 粗筛论文并生成 candidates.csv
python scripts/filter_candidates.py --input data/processed/iclr_2025_papers.csv

# 3. 分类候选并生成 classified.csv
python scripts/classify_papers.py --input data/processed/iclr_2025_candidates.csv

# 4. 生成会议 Markdown 报告
python scripts/generate_report.py --input data/processed/iclr_2025_classified.csv

# 5. 生成精读笔记模板
python scripts/generate_reading_notes.py --input data/processed/iclr_2025_classified.csv

# 6. 生成分享稿大纲模板
python scripts/generate_share_briefs.py --input data/processed/iclr_2025_classified.csv

# 7. 同步到指定笔记软件
python scripts/sync_to_notes.py --input data/processed/iclr_2025_classified.csv --target siyuan --note-type all
```

---

## 8. 输出文件说明 (Output Structure)

运行后项目数据目录和导出目录结构如下：

```text
posttrain-radar/
├── data/
│   ├── raw/
│   │   └── openreview_iclr_2025.json           # 抓取回的原始 JSON
│   ├── processed/
│   │   ├── iclr_2025_papers.csv                 # 标准化后的全部论文
│   │   ├── iclr_2025_candidates.csv             # 粗筛后的候选论文
│   │   └── iclr_2025_classified.csv             # 分类打标后的后训练论文
│   ├── reports/
│   │   └── iclr_2025_posttrain_report.md        # 会议分类与优先级阅读报告
│   ├── reading_notes/
│   │   └── ICLR_2025/
│   │       └── [Paper_Title].md                 # 论文精读卡片模板
│   └── share_briefs/
│       └── ICLR_2025/
│           └── [Paper_Title]_Share_Brief.md     # 组会分享/PPT 大纲模板
```

---

## 9. 笔记软件联动说明 (Note App Integration)

### 思源笔记 (SiYuan Note)
思源同步使用局域网 REST API。请确保思源客户端已打开，并在设置中开启 API。
1. **配置 Token**：在环境变量中设置 `SIYUAN_TOKEN`。
2. **笔记本配置**：在 `config/note_targets.yaml` 中配置 `notebook_name` 为你的笔记本名称（例如 `"PostTrain Radar"`）。
3. **显式校验安全**：同步时不会随意猜测笔记本。若指定的 `notebook_name` 不存在，程序会打印警告、列出所有可用笔记本并安全退出，避免写错地方。
4. **数据库记录**：成功同步后，SQLite 数据库的 `papers` 表中会自动记录 `siyuan_doc_id` 和 `siyuan_path`，便于关联。

### Obsidian
Obsidian 通过写入本地 Vault 路径来实现同步。
1. 在 `config/note_targets.yaml` 中将 `obsidian.enabled` 设为 `true`，并填入 `vault_path`（如 `"/Users/yourname/Documents/MyObsidianVault"`）。
2. 同步目标结构会按照你个人的知识体系自动映射，十分清晰。

### 统一知识库映射目录

同步到思源或 Obsidian 后，会自动挂载至如下知识结构：
```text
PostTrain Radar/
├── 00_Index/
│   ├── ICLR_2025_Report           # 会议优先级报告
│   └── Reading_Queue              # (可选) 待读队列
├── 01_Papers/
│   └── ICLR_2025/
│       └── [Paper_Title]          # 论文卡片 (阅读笔记模板)
├── 05_Share/
│   └── ICLR_2025/
│       └── [Paper_Title]_Share_Brief  # 组会分享大纲
└── 06_Workflows/
    └── Prompts/
        ├── quick_screening_prompt   # 论文快速筛选 Prompt
        ├── deep_reading_prompt      # 论文精读 Prompt
        ├── critical_review_prompt   # 论文批判性复盘 Prompt
        └── share_generation_prompt  # 论文分享生成 Prompt
```

---

## 10. 人工修改保护机制 (Note Preservation)

> [!WARNING]
> 为了保障你写好的读书笔记和组会总结不被后续的自动运行覆盖，系统设计了严密的安全机制。

1. **默认不覆盖**：若文件或 SiYuan 文档已存在，默认只做提示并跳过。
2. **选择性覆盖与自动合并**：当传入 `--overwrite` 参数时，程序会首先读取已存在的笔记内容，**利用 HTML 注释标记自动解析提取出你在 `My Notes` 和 `My Judgment` 区域手动写下的内容**，然后再与最新的元数据进行合并写入。
3. **防覆盖模版结构**：
   ```markdown
   # Paper Reading Note: ...
   
   ## 1. Auto Metadata
   <!-- START_AUTO_METADATA -->
   [这里由系统自动更新，包括阅读状态、优先级等]
   <!-- END_AUTO_METADATA -->
   
   ## 2. AI Draft
   <!-- START_AI_DRAFT -->
   [AI 筛选出的关键词和匹配理由]
   <!-- END_AI_DRAFT -->
   
   ## 3. My Notes
   <!-- START_MY_NOTES -->
   [这里是你在思源/Obsidian里手写的精读笔记，同步时将被原样保留！]
   <!-- END_MY_NOTES -->
   
   ## 4. My Judgment
   <!-- START_MY_JUDGMENT -->
   [这里是你的批判性思考，同步时将被原样保留！]
   <!-- END_MY_JUDGMENT -->
   ```

---

## 11. 后续增强方向 (Future Roadmap)

1. **多数据源扩展**：正式打通 ACL Anthology XML 与 CVF Open Access 页面，提供稳定的多会议元数据搜集。
2. **学术图谱扩充**：集成 Semantic Scholar API，自动抓取论文的引用量 (Citation Count)、经典参考文献、以及相关工作。
3. **语义分类器**：接入 OpenAI API 或本地大语言模型，将 heuristics 分类演进为真正的语义分类器，提升问题痛点和方法的分类准确率。
4. **自动周报生成**：基于每周新入库论文，自动生成“LLM/VLM alignment 每周进展周报”至 `05_Share/Weekly_Reports`。
5. ** Notion / Zotero 适配器**：正式实现 `NotionExporter` 和 `ZoteroExporter`。
6. **Streamlit UI**：增加可视化交互式管理面板。
