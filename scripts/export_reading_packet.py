#!/usr/bin/env python3
import argparse
import os
import sys
import re
import json
import yaml

# Adjust Python path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app import PostTrainRadarApp
from src.note_generator import NoteGenerator, map_method_to_link, map_problem_to_link
from src.share_generator import ShareGenerator
from src.normalizer import normalize_title
from src.exporters.markdown_exporter import safe_filename

def get_safe_filename(title: str) -> str:
    # Remove chars not allowed in file paths
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    # Replace spaces with underscores
    clean = re.sub(r'\s+', '_', clean)
    return clean.strip("_")

def main():
    parser = argparse.ArgumentParser(description="Export a comprehensive Reading Packet for a paper.")
    parser.add_argument("--paper-id", type=int, help="Database paper ID")
    parser.add_argument("--source-id", type=str, help="Source system ID (e.g. OpenReview forum ID or ArXiv ID)")
    parser.add_argument("--title", type=str, help="Paper title")
    parser.add_argument("--venue", type=str, help="Filter by venue")
    parser.add_argument("--year", type=int, help="Filter by year")
    
    args = parser.parse_args()
    
    if not (args.paper_id or args.source_id or args.title):
        parser.error("At least one of --paper-id, --source-id, or --title must be specified.")
        
    app = PostTrainRadarApp()
    
    # Query matching paper based on priority: paper_id > source_id > title + venue/year
    target_paper = None
    
    if args.paper_id:
        papers = app.db.get_classified_papers(venue=None, year=None)
        for p in papers:
            if p["id"] == args.paper_id:
                target_paper = p
                break
    elif args.source_id:
        papers = app.db.get_classified_papers(venue=None, year=None)
        for p in papers:
            if p.get("source_id") and str(p["source_id"]).strip().lower() == str(args.source_id).strip().lower():
                target_paper = p
                break
    elif args.title:
        papers = app.db.get_classified_papers(venue=args.venue, year=args.year)
        target_norm = normalize_title(args.title)
        for p in papers:
            if normalize_title(p["title"]) == target_norm:
                target_paper = p
                break
                
    if not target_paper:
        print("[!] Error: No matching paper found in database.")
        sys.exit(1)
        
    title = target_paper["title"]
    print(f"[*] Found paper: '{title}' (ID: {target_paper['id']})")
    
    # Initialize SiYuan Exporter to check live content
    siyuan_exporter = app.get_exporter("siyuan")
    siyuan_connected = False
    
    if siyuan_exporter:
        # Check connection and validate notebook
        if siyuan_exporter.test_connection() and siyuan_exporter.validate_notebook():
            siyuan_connected = True
            
    # 1. Paper Card 当前内容
    paper_card_content = None
    if siyuan_connected:
        doc_id = target_paper.get("siyuan_doc_id")
        if not doc_id:
            # Try to resolve by path
            source = target_paper.get("source", "").lower()
            status = target_paper.get("status", "").lower()
            venue_safe = safe_filename(target_paper.get("venue", "unknown"))
            year = target_paper.get("year", 2025)
            title_safe = safe_filename(title)
            
            if source in ["openreview", "acl_anthology", "cvf_openaccess"] and status == "accepted":
                target_path = f"/01_Papers/{venue_safe}_{year}/{title_safe}"
            elif source == "arxiv":
                target_path = f"/01_Papers/ArXiv_Preprints/{title_safe}"
            else:
                target_path = f"/01_Papers/Manual_Import/{title_safe}"
                
            doc_id, _ = siyuan_exporter._find_doc_id_and_path(target_path)
            
        if doc_id:
            res = siyuan_exporter._call_api("/api/export/exportMdContent", {"id": doc_id})
            if res and res.get("code") == 0:
                paper_card_content = res.get("data", {}).get("content", "")
                print(f"[+] Loaded Paper Card content from live SiYuan (ID: {doc_id}).")
                
    if not paper_card_content:
        # Fallback to generating on the fly
        paper_card_content = app.note_gen.generate(target_paper)
        print(f"[*] Generated Paper Card content (fallback).")

    # 2. Auto Metadata
    auto_metadata = app.note_gen.extract_section(paper_card_content, "Auto Metadata")
    if not auto_metadata:
        # Fallback to manual metadata construction if section not found
        metadata_rows = [
            f"| Venue | {target_paper.get('venue', 'Unknown')} |",
            f"| Year | {target_paper.get('year', 2025)} |",
            f"| Authors | {', '.join(target_paper.get('authors', []))} |",
            f"| Source | {target_paper.get('source', 'Unknown')} |",
            f"| Status | {target_paper.get('status', 'Unknown')} |",
            f"| Data Origin | {target_paper.get('data_origin', 'Unknown')} |",
            f"| Relevance Level | {target_paper.get('relevance_level', 'D_Irrelevant')} |",
            f"| Confidence | {target_paper.get('confidence', 0.0)} |",
            f"| Reason | {target_paper.get('reason', 'No reason provided.')} |"
        ]
        auto_metadata = (
            "| Metadata Key | Value |\n"
            "| :--- | :--- |\n" +
            "\n".join(metadata_rows)
        )

    # 3. AI Draft Summary
    ai_draft_summary = app.note_gen.extract_section(paper_card_content, "AI Draft Summary")
    if not ai_draft_summary:
        ai_draft_summary = "*No draft summary available.*"

    # 4. Classification Evidence
    classification_evidence = app.note_gen.extract_section(paper_card_content, "Classification Evidence")
    if not classification_evidence:
        classification_evidence = "*No classification evidence recorded.*"

    # 5. Abstract
    abstract = target_paper.get("abstract") or "*No abstract stored in database.*"
    abstract_formatted = "\n".join([f"> {line}" for line in abstract.splitlines()])

    # 6. Method Tags / Problem Tags
    def clean_tags(tag_list) -> str:
        if not tag_list:
            return "None"
        return ", ".join(tag_list)
        
    method_tags_str = clean_tags(target_paper.get("post_training_types", []))
    problem_tags_str = clean_tags(target_paper.get("problem_tags", []))

    # 7. 推荐回流的 Method / Problem 页面
    method_links = []
    for t in target_paper.get("post_training_types", []):
        link = map_method_to_link(t)
        if link:
            method_links.append(link)
    problem_links = []
    for t in target_paper.get("problem_tags", []):
        link = map_problem_to_link(t)
        if link:
            problem_links.append(link)
            
    method_links_str = " ".join(sorted(list(set(method_links)))) if method_links else "待人工补充"
    problem_links_str = " ".join(sorted(list(set(problem_links)))) if problem_links else "待人工补充"

    # 8. Share Brief 草稿
    share_brief = None
    if siyuan_connected:
        venue_upper = safe_filename(target_paper.get("venue", "unknown")).upper()
        year = target_paper.get("year", 2025)
        title_safe = safe_filename(title)
        share_path = f"/05_Share/Group_Meeting/Paper_Briefs/{venue_upper}_{year}/{title_safe}_Share_Brief"
        
        share_doc_id, _ = siyuan_exporter._find_doc_id_and_path(share_path)
        if share_doc_id:
            res = siyuan_exporter._call_api("/api/export/exportMdContent", {"id": share_doc_id})
            if res and res.get("code") == 0:
                share_brief = res.get("data", {}).get("content", "")
                print(f"[+] Loaded Share Brief content from live SiYuan (ID: {share_doc_id}).")
                
    if not share_brief:
        share_brief = app.share_gen.generate(target_paper)
        print(f"[*] Generated Share Brief (fallback).")

    # 9. 阅读助手使用说明
    usage_instructions = """> **使用提示**：本文件是 PostTrain Radar 系统为这篇论文专门生成的精读背景包（Reading Packet）。
> 请直接将此包内容粘贴给 AI 阅读助手（例如新的 Chat Session），并附带如下指令：
> 
> ```text
> 你是一个专业的 AI 论文精读助手。我给你提供了一个关于该论文的 PostTrain Radar 背景数据包（Reading Packet），其中包含了当前论文卡片（Paper Card）、分类元数据、AI 摘要、推荐回流页面和分享大纲草稿。
> 请在阅读该论文的 PDF/原文时，结合我提供的数据包上下文进行以下工作：
> 1. 严格对齐数据包中的 Method Tags 和 Problem Tags 进行扩展和印证，看论文实际内容是否符合这些标签的判定。
> 2. 帮我补充和核实【Auto Metadata】和【AI Draft Summary】中的“一句话总结”、“解决的问题”、“核心方法”与“实验结论”。
> 3. 详细输出论文的核心方法论，以供我回流到相关的知识页中（例如数据包推荐的 Method / Problem 页面）。
> 4. 重点对数据包中【Share Brief 草稿】的各级组会/深度研讨大纲进行细化与内容填充，撰写一份可以直接分享的闪电演讲大纲和技术分享会大纲。
> 
> 让我们开始吧！请先简要向我确认你已完全理解上述指令和数据包背景。
> ```"""

    # Assemble the Reading Packet MD
    packet_md = f"""# Reading Packet: {title}

## 1. Paper Card 当前内容
```markdown
{paper_card_content}
```

## 2. Auto Metadata
{auto_metadata}

## 3. AI Draft Summary
{ai_draft_summary}

## 4. Classification Evidence
{classification_evidence}

## 5. Abstract
{abstract_formatted}

## 6. Method Tags / Problem Tags
- **Method Tags**: {method_tags_str}
- **Problem Tags**: {problem_tags_str}

## 7. 推荐回流的 Method / Problem 页面
- **推荐 Method 页面**: {method_links_str}
- **推荐 Problem 页面**: {problem_links_str}

## 8. Share Brief 草稿
```markdown
{share_brief}
```

## 9. 阅读助手使用说明
{usage_instructions}
"""

    os.makedirs("data/reading_packets", exist_ok=True)
    safe_title = get_safe_filename(title)
    out_path = f"data/reading_packets/{safe_title}_reading_packet.md"
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(packet_md)
        
    print(f"[+] Successfully exported reading packet to: {out_path}")

if __name__ == "__main__":
    main()
