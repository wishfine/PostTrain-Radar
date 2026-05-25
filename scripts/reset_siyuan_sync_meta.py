import argparse
import sys
import os

# Adjust Python path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app import PostTrainRadarApp

def main():
    parser = argparse.ArgumentParser(description="Reset SiYuan sync metadata for a specific venue and year.")
    parser.add_argument("--venue", type=str, required=True, help="Conference venue, e.g. ICLR")
    parser.add_argument("--year", type=int, required=True, help="Conference year, e.g. 2025")
    parser.add_argument("--confirm-reset", action="store_true", help="Confirmation flag required to actually modify the database")

    args = parser.parse_args()

    print(f"=== SiYuan Sync Metadata Reset Tool ===")
    print(f"Target Venue: {args.venue}")
    print(f"Target Year: {args.year}")
    print(f"Confirm Reset: {args.confirm_reset}")
    print(f"=======================================")

    app = PostTrainRadarApp()
    
    # Query database to find papers that have sync metadata for the venue/year
    cursor = app.db.conn.cursor()
    cursor.execute("""
        SELECT p.id, p.title, p.siyuan_doc_id, p.siyuan_path, t.include_in_siyuan
        FROM papers p
        LEFT JOIN paper_tags t ON p.id = t.paper_id
        WHERE p.venue = ? AND p.year = ? 
          AND (p.siyuan_doc_id IS NOT NULL AND p.siyuan_doc_id != '' OR p.siyuan_path IS NOT NULL OR t.include_in_siyuan = 1)
    """, (args.venue, args.year))
    
    rows = cursor.fetchall()
    
    if not rows:
        print("[-] No papers found with active SiYuan sync metadata for this venue/year.")
        sys.exit(0)
        
    print(f"[*] Found {len(rows)} papers with sync metadata to reset.")
    
    if not args.confirm_reset:
        print("\n[*] DRY RUN: Listing papers that would be reset:")
        for idx, row in enumerate(rows, 1):
            print(f"  {idx}. '{row['title']}' (Doc ID: {row['siyuan_doc_id']}, Path: {row['siyuan_path']})")
        print("\n[!] WARNING: This was a dry-run. No changes were made to the database.")
        print("[!] To perform the reset, you MUST re-run this command with: --confirm-reset")
        sys.exit(0)
        
    # If confirm-reset, update the database
    print("\n[*] Resetting sync metadata in database...")
    
    try:
        # Clear fields in papers table
        app.db.conn.execute("""
            UPDATE papers
            SET siyuan_doc_id = NULL,
                siyuan_path = NULL,
                siyuan_sync_time = NULL,
                siyuan_sync_mode = NULL
            WHERE venue = ? AND year = ?
        """, (args.venue, args.year))
        
        # Clear include_in_siyuan in paper_tags table for these papers
        paper_ids = [row["id"] for row in rows]
        placeholders = ",".join("?" for _ in paper_ids)
        app.db.conn.execute(f"""
            UPDATE paper_tags
            SET include_in_siyuan = 0
            WHERE paper_id IN ({placeholders})
        """, paper_ids)
        
        app.db.conn.commit()
        print(f"[+] Successfully reset sync metadata for {len(rows)} papers in database.")
        print("[+] Preserved all manual curation fields (manual_selected, include_in_reading_queue, include_in_share_pool, reviewer_comment).")
    except Exception as e:
        app.db.conn.rollback()
        print(f"[!] Database transaction failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
