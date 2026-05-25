import argparse
import sys
import os
import sqlite3
from datetime import datetime


# Adjust Python path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app import PostTrainRadarApp

def normalize_siyuan_path(path):
    if not path:
        return ""
    p = path.lower().strip().replace("\\", "/")
    if p.endswith(".sy"):
        p = p[:-3]
    return "/" + p.strip("/")

def main():
    parser = argparse.ArgumentParser(description="Validate SiYuan sync metadata in database against SiYuan Note.")
    parser.add_argument("--venue", type=str, help="Filter by venue (e.g. ICLR)")
    parser.add_argument("--year", type=int, help="Filter by year (e.g. 2025)")
    args = parser.parse_args()

    app = PostTrainRadarApp()
    exporter = app.get_exporter("siyuan")
    
    if not exporter.validate_notebook():
        print("[!] Notebook validation failed. Check SiYuan URL / Token / Notebook Name.")
        sys.exit(1)

    # Fetch papers from DB that have siyuan_doc_id
    query = """
        SELECT p.id, p.title, p.venue, p.year, p.siyuan_doc_id, p.siyuan_path, p.siyuan_sync_mode 
        FROM papers p
        WHERE p.siyuan_doc_id IS NOT NULL AND p.siyuan_doc_id != ''
    """
    params = []
    if args.venue:
        query += " AND p.venue = ?"
        params.append(args.venue)
    if args.year:
        query += " AND p.year = ?"
        params.append(args.year)

    cursor = app.db.conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        print("[-] No papers found in database with SiYuan sync metadata.")
        sys.exit(0)

    print(f"[*] Auditing {len(rows)} papers in database against SiYuan Note...")

    results = {
        "active": [],
        "moved": [],
        "archived": [],
        "stale": [],
        "missing_path": []
    }

    for row in rows:
        paper_id = row["id"]
        title = row["title"]
        doc_id = row["siyuan_doc_id"]
        db_path = row["siyuan_path"]
        sync_mode = row["siyuan_sync_mode"]
        venue = row["venue"]
        year = row["year"]

        # Call SiYuan API to get actual hpath
        res = exporter._call_api("/api/filetree/getHPathByID", {"id": doc_id})
        
        if not res or res.get("code") != 0 or not res.get("data"):
            # Cannot find the document in SiYuan -> stale
            results["stale"].append({
                "title": title, "doc_id": doc_id, "db_path": db_path, "venue": venue, "year": year
            })
            continue

        actual_hpath = res.get("data")
        norm_actual = normalize_siyuan_path(actual_hpath)
        norm_db = normalize_siyuan_path(db_path)

        # Check if actual path starts with archive directory
        is_archived = norm_actual.startswith("/99_archive/bulk_imported")

        if is_archived:
            results["archived"].append({
                "title": title, "doc_id": doc_id, "db_path": db_path, "actual_path": actual_hpath, "venue": venue, "year": year
            })
        elif not db_path or str(db_path).strip() == "":
            results["missing_path"].append({
                "title": title, "doc_id": doc_id, "actual_path": actual_hpath, "venue": venue, "year": year
            })
        elif norm_actual == norm_db:
            results["active"].append({
                "title": title, "doc_id": doc_id, "db_path": db_path, "venue": venue, "year": year
            })
        else:
            results["moved"].append({
                "title": title, "doc_id": doc_id, "db_path": db_path, "actual_path": actual_hpath, "venue": venue, "year": year
            })

    report_lines = []
    report_lines.append("# SiYuan Sync Metadata Validation Report")
    report_lines.append(f"- **Audited At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"- **Venue Filter**: {args.venue if args.venue else 'All'}")
    report_lines.append(f"- **Year Filter**: {args.year if args.year else 'All'}")
    report_lines.append(f"- **Total Synced Papers Audited**: {len(rows)}")
    report_lines.append("")
    report_lines.append("## Status Summary")
    report_lines.append(f"- **Active (In Sync)**: {len(results['active'])}")
    report_lines.append(f"- **Moved (Path Mismatch)**: {len(results['moved'])}")
    report_lines.append(f"- **Archived (In Archive Folder)**: {len(results['archived'])}")
    report_lines.append(f"- **Stale (Missing from SiYuan)**: {len(results['stale'])}")
    report_lines.append(f"- **Missing Path (No DB path)**: {len(results['missing_path'])}")
    report_lines.append("")
    report_lines.append("## Detailed Results")

    for status, items in results.items():
        report_lines.append(f"### {status.upper()} ({len(items)} papers)")
        if not items:
            report_lines.append("*None*")
            report_lines.append("")
            continue
        for idx, item in enumerate(items, 1):
            report_lines.append(f"{idx}. **{item['title']}**")
            report_lines.append(f"   - **Doc ID**: `{item['doc_id']}`")
            report_lines.append(f"   - **Venue/Year**: {item['venue']} {item['year']}")
            if status == "moved":
                report_lines.append(f"   - **Recorded DB Path**: `{item['db_path']}`")
                report_lines.append(f"   - **Actual SiYuan Path**: `{item['actual_path']}`")
            elif status == "archived":
                report_lines.append(f"   - **Actual SiYuan Path**: `{item['actual_path']}`")
            elif status == "stale":
                report_lines.append(f"   - **Recorded DB Path**: `{item['db_path']}`")
            elif status == "missing_path":
                report_lines.append(f"   - **Actual SiYuan Path**: `{item['actual_path']}`")
        report_lines.append("")

    report_md = "\n".join(report_lines)

    # Print to console
    print("\n" + "="*50)
    print("=== SiYuan Metadata Validation Report ===")
    print("="*50)
    print(f"Total Synced Papers Audited: {len(rows)}")
    print(f"  - Active (In Sync): {len(results['active'])}")
    print(f"  - Moved (Path Mismatch): {len(results['moved'])}")
    print(f"  - Archived (In Archive Folder): {len(results['archived'])}")
    print(f"  - Stale (Missing from SiYuan): {len(results['stale'])}")
    print(f"  - Missing Path (No DB path): {len(results['missing_path'])}")
    print("="*50)

    for status, items in results.items():
        if items:
            print(f"\n[{status.upper()}] ({len(items)} papers):")
            for idx, item in enumerate(items, 1):
                msg = f"  {idx}. '{item['title']}' (ID: {item['doc_id']}) in {item['venue']} {item['year']}"
                if status == "moved":
                    msg += f"\n     Recorded Path: {item['db_path']}\n     Actual Path:   {item['actual_path']}"
                elif status == "archived":
                    msg += f"\n     Actual Path:   {item['actual_path']}"
                elif status == "stale":
                    msg += f"\n     Recorded Path: {item['db_path']}"
                elif status == "missing_path":
                    msg += f"\n     Actual Path:   {item['actual_path']}"
                print(msg)

    # Save report to file
    report_dir = "data/reports"
    os.makedirs(report_dir, exist_ok=True)
    v_str = args.venue.lower() if args.venue else "all"
    y_str = str(args.year) if args.year else "all"
    report_path = os.path.join(report_dir, f"siyuan_sync_meta_validation_{v_str}_{y_str}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n[+] Validation report saved to: {report_path}")
    print("[+] Validation finished. No database changes were made.")

if __name__ == "__main__":
    main()
