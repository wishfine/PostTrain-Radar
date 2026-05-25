import argparse
import sys
import os
import sqlite3
import json
import re
from datetime import datetime

# Adjust Python path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app import PostTrainRadarApp
from src.normalizer import normalize_title

notes_boilerplate = [
    "> [!IMPORTANT]",
    "*人工阅读记录。任何自动同步工具均绝对禁止覆盖或清空此分区。*",
    "*   **阅读时间**:",
    "*   **精读笔记**:",
    "    *   (在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)"
]

judgment_boilerplate = [
    "> [!IMPORTANT]",
    "*人工思考与批判性判断。任何自动同步工具均绝对禁止覆盖或清空此分区。*",
    "*   **论文盲点/局限性**:",
    "*   **实验设计局限**:",
    "*   **我的评价**:",
    "    *   (在这里写下您对该文的真实技术评价，是否真正解决了痛点？)"
]

review_boilerplate = [
    "> [!IMPORTANT]",
    "*人工对 AI 生成草稿的审查记录，自动更新不会覆盖。*",
    "*   **AI Draft 是否可信**: High / Medium / Low",
    "*   **错误点**:",
    "*   **我修正后的理解**:",
    "*   **是否需要重新生成**:"
]

def has_human_content(content: str) -> bool:
    from src.note_generator import NoteGenerator
    
    # Extract the user input sections
    notes = NoteGenerator.extract_section(content, "My Reading Notes") or ""
    judgment = NoteGenerator.extract_section(content, "My Judgment") or ""
    review = NoteGenerator.extract_section(content, "AI Draft Review") or ""
    
    # Helper to clean and check
    def is_empty_or_boilerplate(text, boilerplates):
        cleaned = text.strip()
        if not cleaned:
            return True
        # Remove HTML comments and Obsidian callout headers to clean old note remnants
        cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r">\s*\[\!.*?\]", "", cleaned)
        # Remove common boilerplate lines
        for bp in boilerplates:
            cleaned = cleaned.replace(bp, "")
        
        # Remove common Chinese/English boilerplate keywords to prevent false positives
        keywords = ["人工阅读记录", "自动同步工具", "绝对禁止覆盖", "阅读时间", "精读笔记", "在此记录", "阅读细节", 
                    "人工思考", "批判性判断", "论文盲点", "局限性", "实验设计局限", "我的评价", "真实技术评价",
                    "人工对AI", "生成草稿的审查", "自动更新不会覆盖", "是否可信", "错误点", "我修正后的理解", "是否需要重新生成"]
        for kw in keywords:
            cleaned = cleaned.replace(kw, "")
            
        # Strip all formatting characters and spaces
        cleaned = re.sub(r'[\s\*\-\:\>\!\[\]\(\)\n]', '', cleaned)
        return len(cleaned) == 0

    notes_empty = is_empty_or_boilerplate(notes, notes_boilerplate)
    judgment_empty = is_empty_or_boilerplate(judgment, judgment_boilerplate)
    review_empty = is_empty_or_boilerplate(review, review_boilerplate)
    
    return not (notes_empty and judgment_empty and review_empty)

def matches_keep_scope(paper_data: dict, keep_scope: str) -> bool:
    is_selected = (
        paper_data.get("include_in_siyuan") == 1 or 
        paper_data.get("manual_selected") == 1 or 
        paper_data.get("include_in_reading_queue") == 1 or
        paper_data.get("is_core_posttraining") == 1 or
        paper_data.get("relevance_level") == "A_Core_PostTraining"
    )
    is_a_core = (
        paper_data.get("relevance_level") == "A_Core_PostTraining" or 
        paper_data.get("is_core_posttraining") == 1
    )
    is_high_prio = (paper_data.get("priority") == "High")
    is_worth_sharing = (
        paper_data.get("share_status") == "WorthSharing" or 
        (paper_data.get("share_status") and "WorthSharing" in paper_data.get("share_status")) or 
        paper_data.get("include_in_share_pool") == 1
    )
    
    if keep_scope == "all":
        return True
    elif keep_scope == "selected":
        return is_selected
    elif keep_scope == "high":
        return (is_high_prio and is_a_core) or is_selected
    elif keep_scope == "core":
        return is_a_core or is_selected
    elif keep_scope == "worth_sharing":
        if paper_data.get("relevance_level") == "D_Irrelevant":
            return (paper_data.get("manual_selected") == 1)
        else:
            return is_worth_sharing or is_selected
            
    return is_selected

def ensure_archive_folder_id(exporter, archive_folder_path, venue, year):
    doc_id, doc_path = exporter._find_doc_id_and_path(archive_folder_path)
    if doc_id:
        return doc_id
        
    if exporter.dry_run:
        print(f"[*] [DRY-RUN] Would create archive folder doc at: {archive_folder_path}")
        return "dry_run_archive_parent_id"
        
    res = exporter._call_api("/api/filetree/createDocWithMd", {
        "notebook": exporter.notebook_id,
        "path": archive_folder_path,
        "markdown": f"# Archived Papers {venue} {year}\nArchived on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    })
    
    if res and res.get("code") == 0:
        new_id = res.get("data")
        print(f"[+] Created archive folder doc: {archive_folder_path} (ID: {new_id})")
        return new_id
    else:
        print(f"[!] Failed to create archive folder doc: {res}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Cleanup and Archive/Delete unselected papers from SiYuan notebook.")
    parser.add_argument("--venue", type=str, required=True, help="Conference venue, e.g. ICLR")
    parser.add_argument("--year", type=int, required=True, help="Conference year, e.g. 2025")
    parser.add_argument("--mode", type=str, choices=["archive", "delete"], default="archive", help="Archive or delete matched papers")
    parser.add_argument("--keep-scope", type=str, choices=["selected", "high", "core", "worth_sharing", "all"], default="selected", help="Retention scope for papers")
    parser.add_argument("--archive-to", type=str, default="/99_Archive/Bulk_Imported", help="Parent document path inside notebook to archive documents to")
    parser.add_argument("--source", type=str, choices=["db", "path_scan"], default="db", help="Source for scanning papers (SQLite DB or SiYuan API scan)")
    parser.add_argument("--confirm-delete", action="store_true", help="Confirmation flag for deleting documents")
    parser.add_argument("--i-understand-this-will-remove-siyuan-docs", action="store_true", help="Safety check required to run delete mode")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run without actually making API requests to SiYuan")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Disable dry run and make actual changes")

    args = parser.parse_args()

    if args.mode == "delete":
        if not args.confirm_delete or not args.i_understand_this_will_remove_siyuan_docs:
            print("[!] ERROR: You are running in 'delete' mode. This will permanently remove documents from SiYuan.")
            print("To proceed, you MUST pass both --confirm-delete and --i-understand-this-will-remove-siyuan-docs.")
            sys.exit(1)

    print(f"=== Starting SiYuan Cleanup/Archive Script ===")
    print(f"Conference: {args.venue} {args.year}")
    print(f"Mode: {args.mode.upper()}")
    print(f"Source Type: {args.source.upper()}")
    print(f"Retention Scope: {args.keep_scope}")
    print(f"Dry Run: {args.dry_run}")
    print("==============================================")

    # Initialize app and exporter
    app = PostTrainRadarApp()
    exporter = app.get_exporter("siyuan", dry_run=args.dry_run)
    if not exporter.validate_notebook():
        print("[!] Notebook validation failed. Check SiYuan URL / Token / Notebook Name.")
        sys.exit(1)

    # Collect paper references depending on --source
    papers_to_check = []
    
    if args.source == "db":
        # Get from DB matching venue and year
        db_papers = app.db.get_classified_papers(args.venue, args.year)
        for p in db_papers:
            if p.get("siyuan_doc_id") and p.get("siyuan_path"):
                papers_to_check.append({
                    "id": p["siyuan_doc_id"],
                    "path": p["siyuan_path"],
                    "title": p["title"],
                    "title_norm": p["title_norm"],
                    "db_record": p
                })
        print(f"[+] Found {len(papers_to_check)} papers in database synced with SiYuan.")
        
    elif args.source == "path_scan":
        # Scan only:
        # - /01_Papers/{venue}_{year}
        # - /01_Papers/ArXiv_Preprints
        # - /01_Papers/Manual_Import
        scan_paths = [
            f"/01_Papers/{args.venue}_{args.year}",
            "/01_Papers/ArXiv_Preprints",
            "/01_Papers/Manual_Import"
        ]
        
        # Get DB papers once for lookups
        db_papers_all = app.db.get_classified_papers()
        db_by_title_norm = {p["title_norm"]: p for p in db_papers_all}
        
        for base_path in scan_paths:
            print(f"[*] Scanning path: {base_path} ...")
            res = exporter._call_api("/api/filetree/listDocsByPath", {
                "notebook": exporter.notebook_id,
                "path": base_path
            })
            if not res or res.get("code") != 0:
                print(f"[-] Path not found or API error listing: {base_path}")
                continue
                
            files = res.get("data", {}).get("files", [])
            print(f"    - Found {len(files)} files in path {base_path}")
            
            for f in files:
                name = f.get("name", "")
                doc_id = f.get("id")
                doc_path = f.get("path")
                
                title = name[:-3] if name.endswith(".sy") else name
                title_norm = normalize_title(title)
                
                # Check DB lookup
                db_record = db_by_title_norm.get(title_norm)
                
                if base_path.startswith("/01_Papers/ArXiv_Preprints") or base_path.startswith("/01_Papers/Manual_Import"):
                    # For these paths, must be in DB and match target venue/year
                    if not db_record:
                        continue
                    if db_record.get("venue") != args.venue or db_record.get("year") != args.year:
                        continue
                else:
                    # For /01_Papers/{venue}_{year}, if in DB and doesn't match venue/year, skip
                    if db_record and (db_record.get("venue") != args.venue or db_record.get("year") != args.year):
                        continue
                        
                papers_to_check.append({
                    "id": doc_id,
                    "path": doc_path,
                    "title": title,
                    "title_norm": title_norm,
                    "db_record": db_record
                })
                
        print(f"[+] Total papers gathered from scan: {len(papers_to_check)}")

    # Process each paper
    keep_count = 0
    skipped_user_content_count = 0
    archived_count = 0
    deleted_count = 0
    failed_count = 0
    
    archive_parent_id = None
    if args.mode == "archive" and len(papers_to_check) > 0:
        archive_folder_path = f"{args.archive_to}/{args.venue}_{args.year}_{datetime.now().strftime('%Y%m%d')}"
        archive_parent_id = ensure_archive_folder_id(exporter, archive_folder_path, args.venue, args.year)
        if not archive_parent_id:
            print("[!] Failed to ensure archive parent folder ID. Aborting execution.")
            sys.exit(1)

    for item in papers_to_check:
        doc_id = item["id"]
        doc_path = item["path"]
        title = item["title"]
        db_rec = item["db_record"]
        
        # 1. Scope Retention Check
        in_scope = False
        if db_rec:
            in_scope = matches_keep_scope(db_rec, args.keep_scope)
            
        if in_scope:
            print(f"[-] KEEP: '{title}' matches keep scope '{args.keep_scope}'.")
            keep_count += 1
            continue
            
        # 2. Human Content Safety Check
        content_res = exporter._call_api("/api/export/exportMdContent", {"id": doc_id})
        has_human = False
        if content_res and content_res.get("code") == 0:
            md_content = content_res.get("data", {}).get("content", "")
            has_human = has_human_content(md_content)
        else:
            # If API is dry-run and not connected, print simulation message
            if args.dry_run and not exporter.token:
                has_human = False
            else:
                print(f"[!] Warning: Failed to fetch content for '{title}' (ID: {doc_id}). Skipping safety content check.")
                
        if has_human:
            print(f"[-] KEEP: '{title}' contains user-written human notes.")
            skipped_user_content_count += 1
            continue
            
        # 3. Perform Archive / Delete
        if args.mode == "archive":
            if args.dry_run:
                print(f"[*] [DRY-RUN] Would ARCHIVE '{title}' -> moving to ID {archive_parent_id}")
                archived_count += 1
            else:
                res = exporter._call_api("/api/filetree/moveDocsByID", {
                    "fromIDs": [doc_id],
                    "toID": archive_parent_id
                })
                if res and res.get("code") == 0:
                    print(f"[+] ARCHIVED: '{title}' successfully moved to archive parent.")
                    if db_rec:
                        now = datetime.now().isoformat()
                        new_path = f"{archive_folder_path}/{title}.sy"
                        app.db.conn.execute(
                            "UPDATE papers SET siyuan_path = ?, siyuan_sync_time = ?, siyuan_sync_mode = 'archived' WHERE id = ?",
                            (new_path, now, db_rec["id"])
                        )
                        app.db.conn.execute(
                            "UPDATE paper_tags SET include_in_siyuan = 0 WHERE paper_id = ?",
                            (db_rec["id"],)
                        )
                        app.db.conn.commit()
                        print(f"    - Updated database sync meta for '{title}' (siyuan_sync_mode='archived', include_in_siyuan=0)")
                    archived_count += 1
                else:
                    print(f"[!] Failed to archive '{title}': {res}")
                    failed_count += 1
        elif args.mode == "delete":
            if args.dry_run:
                print(f"[*] [DRY-RUN] Would DELETE '{title}' (ID: {doc_id})")
                deleted_count += 1
            else:
                res = exporter._call_api("/api/filetree/removeDocByID", {
                    "notebook": exporter.notebook_id,
                    "id": doc_id
                })
                if res and res.get("code") == 0:
                    print(f"[+] DELETED: '{title}' successfully deleted.")
                    # Clear siyuan meta from DB if it exists
                    if db_rec:
                        app.db.update_siyuan_meta(db_rec["id"], "", "")
                    deleted_count += 1
                else:
                    print(f"[!] Failed to delete '{title}': {res}")
                    failed_count += 1

    print("\n================ Cleanup Summary ================")
    print(f"Processed: {len(papers_to_check)}")
    print(f"Kept (Matches Scope): {keep_count}")
    print(f"Kept (Contains Human Content): {skipped_user_content_count}")
    if args.mode == "archive":
        print(f"Archived: {archived_count}")
    else:
        print(f"Deleted: {deleted_count}")
    print(f"Failed: {failed_count}")
    print("=================================================")

if __name__ == "__main__":
    main()
