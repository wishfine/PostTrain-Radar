import os
from src.exporters.markdown_exporter import safe_filename

class KnowledgeBackflow:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir

    def run(self, papers: list, patch_scope: str = "high") -> dict:
        """
        Analyzes the list of papers and generates:
        1. 00_Index/知识回流建议.md
        2. data/knowledge_patches/
        """
        relevant_papers = []
        for p in papers:
            if not p.get("is_relevant"):
                continue
            
            is_a_core = (p.get("relevance_level") == "A_Core_PostTraining" or p.get("is_core_posttraining") == 1)
            is_manual_selected = (p.get("include_in_knowledge_patches") == 1)
            is_high_prio = (p.get("priority") == "High")
            
            if patch_scope == "high":
                if is_a_core or is_manual_selected:
                    relevant_papers.append(p)
            elif patch_scope == "selected":
                if is_a_core or is_high_prio or is_manual_selected:
                    relevant_papers.append(p)
            elif patch_scope == "all":
                relevant_papers.append(p)
        
        suggestions = []
        suggestions.append("# 🧭 知识回流建议 (Knowledge Backflow Suggestions)")
        suggestions.append("")
        suggestions.append("本页面根据本次运行发现的前沿论文及其打标结果，推荐应将哪些论文归档挂载至核心知识页（Topics/Methods/Problems）。")
        suggestions.append("")

        patches = {}  # Map (type, tag_name) -> list of paper details

        if not relevant_papers:
            suggestions.append("*本次没有筛选到高相关论文，暂无回流建议。*")
        else:
            suggestions.append("| 序号 | 论文名称 | 会议 | 模型类型 | 方法类型 | 痛点问题 | 推荐回流页面 |")
            suggestions.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            
            for idx, p in enumerate(relevant_papers, 1):
                links = []
                title = p.get("title")
                venue = p.get("venue")
                year = p.get("year")
                m_type = p.get("model_type")
                
                # Check Topics mapping
                if m_type == "LLM":
                    links.append("[[LLM_PostTraining]]")
                    patches.setdefault(("Topics", "LLM_PostTraining"), []).append(p)
                elif m_type == "VLM":
                    links.append("[[VLM_PostTraining]]")
                    patches.setdefault(("Topics", "VLM_PostTraining"), []).append(p)
                elif m_type == "Video-LMM":
                    links.append("[[Video-LMM Post-training]]")
                    patches.setdefault(("Topics", "Video-LMM Post-training"), []).append(p)
                elif m_type == "Agent":
                    links.append("[[Agent_PostTraining]]")
                    patches.setdefault(("Topics", "Agent_PostTraining"), []).append(p)

                # Check Methods mapping
                for m in p.get("post_training_types", []):
                    if "SFT" in m or "Instruction" in m:
                        links.append("[[SFT]]")
                        patches.setdefault(("Methods", "SFT"), []).append(p)
                    elif "PPO" in m or "RLHF" in m:
                        links.append("[[RLHF]]")
                        patches.setdefault(("Methods", "RLHF"), []).append(p)
                    elif "DPO" in m or "Preference" in m:
                        links.append("[[DPO]]")
                        patches.setdefault(("Methods", "DPO"), []).append(p)
                    elif "GRPO" in m or "Reasoning" in m:
                        links.append("[[GRPO]]")
                        patches.setdefault(("Methods", "GRPO"), []).append(p)
                    elif "Reward Modeling" in m:
                        links.append("[[Reward_Modeling]]")
                        patches.setdefault(("Methods", "Reward_Modeling"), []).append(p)
                    elif "Test-Time" in m:
                        links.append("[[Test_Time_Scaling]]")
                        patches.setdefault(("Methods", "Test_Time_Scaling"), []).append(p)
                    elif "Multimodal Alignment" in m:
                        links.append("[[Multimodal_Alignment]]")
                        patches.setdefault(("Methods", "Multimodal_Alignment"), []).append(p)

                # Check Problems mapping
                for prob in p.get("problem_tags", []):
                    # Clean symbol spaces
                    prob_safe = prob.replace(" ", "_")
                    links.append(f"[[{prob_safe}]]")
                    patches.setdefault(("Problems", prob), []).append(p)

                # Stringify fields
                methods_str = ", ".join(p.get("post_training_types", []))
                probs_str = ", ".join(p.get("problem_tags", []))
                links_str = " | ".join(links) if links else "N/A"
                
                suggestions.append(
                    f"| {idx} | {title} | {venue} {year} | {m_type} | {methods_str} | {probs_str} | {links_str} |"
                )

        suggestions_content = "\n".join(suggestions)
        
        # 1. Save suggestions file to reports
        rep_dir = os.path.join(self.output_dir, "reports")
        os.makedirs(rep_dir, exist_ok=True)
        sug_path = os.path.join(rep_dir, "knowledge_backflow_suggestions.md")
        with open(sug_path, "w", encoding="utf-8") as f:
            f.write(suggestions_content)
        print(f"[+] Generated knowledge backflow suggestions at {sug_path}")

        # 2. Generate individual Knowledge Patches
        patch_base_dir = os.path.join(self.output_dir, "knowledge_patches")
        os.makedirs(patch_base_dir, exist_ok=True)

        for (ptype, tag_name), papers_list in patches.items():
            category_dir = os.path.join(patch_base_dir, ptype)
            os.makedirs(category_dir, exist_ok=True)
            
            tag_filename = safe_filename(tag_name)
            patch_file_path = os.path.join(category_dir, f"{tag_filename}.md")

            patch_lines = []
            patch_lines.append(f"# Knowledge Patch: {ptype} - {tag_name}")
            patch_lines.append("")
            patch_lines.append(f"> [!NOTE]\n> 以下是 PostTrain Radar 自动收集的关于 **{tag_name}** 的新文献摘要。你可以直接将这些片段追加到你的 [[{tag_name}]] 知识页中。")
            patch_lines.append("")

            for p in papers_list:
                authors_str = ", ".join(p.get("authors", []))
                matched_kws = ", ".join(p.get("keywords_matched", []))
                
                patch_lines.append(f"### 📚 [{p.get('title')}]({p.get('paper_url') or '#'})")
                patch_lines.append(f"- **会议/年份**: {p.get('venue')} {p.get('year')}")
                patch_lines.append(f"- **作者**: {authors_str}")
                patch_lines.append(f"- **相关度打分**: {p.get('confidence')}")
                patch_lines.append(f"- **研究局限/契合痛点**: {p.get('reason')}")
                patch_lines.append(f"- **匹配证据**: {matched_kws}")
                patch_lines.append(f"- **摘要提炼**: {p.get('abstract')}")
                patch_lines.append("")

            patch_content = "\n".join(patch_lines)
            with open(patch_file_path, "w", encoding="utf-8") as f:
                f.write(patch_content)
            
        print(f"[+] Generated {len(patches)} knowledge patches under {patch_base_dir}")
        return {
            "suggestions_path": sug_path,
            "patches_count": len(patches)
        }
