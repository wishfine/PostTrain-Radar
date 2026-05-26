# 🧭 PostTrain Radar

A top-conference paper tracking and taxonomy system for LLM/VLM post-training research.

---

## 1. 项目简介 (Introduction)

**PostTrain Radar** 是一个面向学术研究者与大模型全栈工程师的前沿论文追踪、筛选、分类与分享辅助系统。它用于搜集顶级人工智能会议（ICLR 等）的论文，自动筛选出与 **LLM/VLM 后训练 (Post-Training) / 对齐 (Alignment) / 推理强化学习 (Reasoning RL)** 相关的论文，并辅助生成结构化的阅读笔记与分享报告。

---

## 2. 核心定位 (Positioning)

> [!IMPORTANT]
> **思源/Obsidian 知识库是精选阅读空间 (Curated Workspace)，而不是全量论文数据库 (Full Paper Database)。**
> 1. **默认不全量同步**：分类器的自动规则分类仅作为“候选推荐”，不能直接决定论文同步。
> 2. **人工批准入口**：`data/manual/tag_overrides.yaml` 是论文进入知识库的**唯一准入通道**。
> 3. **保护手写笔记**：系统永远禁止覆盖人工填写的研究心得（如 `My Reading Notes`, `My Judgment` 等）。

---

## 3. 标准日常使用流程 (9-Step Daily Workflow)

日常推荐的完整阅读与管理流程如下：

### Step 1：本地分类与抓取 (Scraping & Local Classification)
运行以下命令，仅在本地生成数据，**不向思源/Obsidian 写入任何数据**：
```bash
python run_pipeline.py --venue ICLR --year 2025 --sync-target markdown
```
*本地将生成/更新*：
- `data/processed/iclr_2025_classified.csv`
- `data/reports/run_summary_iclr_2025.md`
- `data/00_Index/Reading_Queue_Full.md` (全量队列，仅限本地)

### Step 2：生成重写候选 (Generate Candidates)
提取本期的高价值与高可信度候选论文模板：
```bash
python scripts/generate_override_candidates.py --venue ICLR --year 2025 --top-k 50
```
这会在本地生成候选 YAML 列表 `data/manual/tag_overrides_candidates_iclr_2025.yaml`。为了安全，所有人工准入开关默认均为 `false`。

### Step 3：人工编辑审核 (Manual Selection)
打开生成的 `tag_overrides_candidates_iclr_2025.yaml`，挑选感兴趣的论文，拷贝至 **`data/manual/tag_overrides.yaml`** 中，并根据需求修改其准入开关。

### Step 4：精选阅读队列生成 (Curated Reading Queue)
在运行同步时，系统会基于 `tag_overrides.yaml` 中标记为 `true` 的精选论文，自动在本地生成清爽的 `data/00_Index/精选阅读队列.md`（不再自动塞入未经挑选的 Core 或 High Priority 论文）。

### Step 5：同步预运行检查 (Selected Dry-Run)
同步到思源前，必须先进行 dry-run 以检查同步计划：
```bash
python run_pipeline.py --venue ICLR --year 2025 --sync-target siyuan --siyuan-scope selected --dry-run
```
系统会生成并更新本地的 `data/reports/siyuan_sync_plan_iclr_2025.md`。

### Step 6：正式执行精选同步 (Selected Sync)
确认同步计划无误后，正式推送到思源：
```bash
python run_pipeline.py --venue ICLR --year 2025 --sync-target siyuan --siyuan-scope selected
```
*思源只同步*：
- `00_Index/精选阅读队列` (人工勾选的精选论文)
- `01_Papers/` 下的精选论文卡片
- `05_Share/` 下的精选/分享候选的分享稿
- 必要索引与工作流 Prompt

### Step 7：导出精读背景包 (Export Reading Packet)
为准备精读的论文导出阅读背景包，不直接写入思源：
```bash
python scripts/export_reading_packet.py --title "Paper Title"
```
这会输出至本地 `data/reading_packets/{safe_title}_reading_packet.md`。如果该论文未在 `tag_overrides.yaml` 中被精选，控制台会打印 Warning 警告，但仍允许继续导出。

### Step 8：AI 辅助精读 (AI Reading Session)
将导出的 `reading_packet.md` 粘贴给 AI 阅读助手开展精读。

### Step 9：人工确认并写回笔记 (Manual Write-Back)
AI 阅读助手产生的笔记和批判判断为草稿。**必须由用户审核确认后，手动写回思源笔记卡片**中的 `My Reading Notes` / `My Judgment` / `Knowledge Extraction` 等保护区域。

---

## 4. 人工精选开关定义 (Manual Overrides Semantics)

在 `data/manual/tag_overrides.yaml` 中，你可以为每篇精选论文设定以下控制标记：

- **`manual_selected: true`**：表示我认可这篇论文，它是精选文章。
- **`include_in_siyuan: true`**：允许该论文同步进思源笔记。
- **`include_in_reading_queue: true`**：表示该论文进入精选阅读队列（`精选阅读队列.md`）。
- **`include_in_share_pool: true`**：表示该论文进入组会分享候选池。

### 推荐配置格式
```yaml
papers:
  "direct preference optimization with relative entropy regularization":
    manual_selected: true
    include_in_siyuan: true
    include_in_reading_queue: true
    include_in_knowledge_patches: true
    include_in_share_pool: false
    priority: "High"
    reading_status: "Unread"
    share_status: "Maybe"
    reviewer_comment: "Why I selected this paper."
```

---

## 5. 同步范围选项说明 (SiYuan Sync Scopes)

### 🌟 日常唯一推荐方式
*   **`--siyuan-scope selected` (默认)**：只同步在 `tag_overrides.yaml` 中勾选了 `manual_selected`/`include_in_siyuan`/`include_in_reading_queue` 之一的人工批准论文。

### ⚠️ 临时调试与特定分享模式 (非日常推荐)
*   `none`：调试模式，不同步任何论文。
*   `index_only`：只同步索引页面与 Workflow templates。
*   `high`：只同步 High 优先级 Core 论文 + 人工精选论文。
*   `core`：只同步 Core 级论文 + 人工精选论文。
*   `worth_sharing`：只同步 `WorthSharing` 分享候选论文 + 人工精选论文。
*   `all`：危险模式，全量同步所有候选。**必须显式附带 `--confirm-all-sync`**，防止撑爆工作台。

---

## 6. 人工修改保护机制 (Preservation Mechanism)

为了保障你写好的读书笔记、批判性思考不被后续的自动运行覆盖，系统设计了严密的安全机制：

1. **默认不覆盖**：若 SiYuan 文档已存在，默认只做提示并跳过。
2. **选择性合并**：当传入 `--overwrite` 参数时，程序会首先解析并备份已存在卡片中的以下四个核心保护区，然后再与最新的元数据和 AI Draft Summary 进行合并写入：
   - `## AI Draft Review`
   - `## My Reading Notes`
   - `## My Judgment`
   - `## Knowledge Backfeed Status`
3. **安全清理**：清理脚本 `scripts/cleanup_siyuan.py` 绝对不会删除/归档已包含手写内容（上述保护区非空）的论文页面。

---

## 7. 典型命令行列表 (Typical Commands)

```bash
# 1. 本地更新元数据 (仅本地，不同步思源)
python run_pipeline.py --venue ICLR --year 2025 --sync-target markdown

# 2. 生成候选列表
python scripts/generate_override_candidates.py --venue ICLR --year 2025 --top-k 50

# 3. 预检同步计划 (Dry-run)
python run_pipeline.py --venue ICLR --year 2025 --sync-target siyuan --siyuan-scope selected --dry-run

# 4. 执行精选同步 (Sync)
python run_pipeline.py --venue ICLR --year 2025 --sync-target siyuan --siyuan-scope selected

# 5. 导出精读背景包
python scripts/export_reading_packet.py --title "How to Evaluate Reward Models for RLHF"

# 6. 模拟清理多余文档
python scripts/cleanup_siyuan.py --venue ICLR --year 2025 --mode archive --keep-scope selected --dry-run
```
