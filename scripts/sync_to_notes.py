import os
import argparse
import re
import sys
from src.app import PostTrainRadarApp

def main():
    parser = argparse.ArgumentParser(description="Synchronize papers and reports to note apps")
    parser.add_argument(
        "--input", 
        type=str, 
        required=True, 
        help="Input CSV path (e.g. data/processed/iclr_2025_classified.csv)"
    )
    parser.add_argument(
        "--target", 
        type=str, 
        required=True, 
        choices=["markdown", "siyuan", "obsidian", "notion", "zotero"], 
        help="Target note app / directory adapter"
    )
    parser.add_argument(
        "--note-type", 
        type=str, 
        default="all", 
        choices=["all", "report", "reading_notes", "share_briefs"], 
        help="Note types to synchronize"
    )
    parser.add_argument(
        "--overwrite", 
        action="store_true", 
        help="Overwrite existing documents (merging and preserving human text blocks)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run sync in simulation mode (no writes to filesystem/APIs/database runs)"
    )
    parser.add_argument(
        "--siyuan-scope",
        type=str,
        default="selected",
        choices=["none", "index_only", "selected", "high", "core", "worth_sharing", "all"],
        help="Filter scope of papers to sync to SiYuan notes"
    )
    parser.add_argument(
        "--max-siyuan-notes",
        type=int,
        default=30,
        help="Maximum number of paper cards to sync to SiYuan (0 for unlimited)"
    )
    parser.add_argument(
        "--patch-scope",
        type=str,
        default="selected",
        choices=["selected", "high", "core", "all"],
        help="Scope of papers to generate knowledge patches for"
    )
    parser.add_argument(
        "--confirm-all-sync",
        action="store_true",
        help="Required confirmation flag if --siyuan-scope is 'all'"
    )

    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input CSV not found at: {input_path}")

    # Deduce venue and year from filename
    base_name = os.path.basename(input_path).lower()
    match = re.search(r"([a-z]+)_(\d{4})", base_name)
    if match:
        venue = match.group(1).upper()
        year = int(match.group(2))
    else:
        venue = "ICLR"
        year = 2025

    app = PostTrainRadarApp()

    print(f"[*] Starting note synchronization to target: {args.target}...")
    try:
        success = app.run_sync(
            venue=venue, 
            year=year, 
            target_type=args.target, 
            note_type=args.note_type, 
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            siyuan_scope=args.siyuan_scope,
            max_siyuan_notes=args.max_siyuan_notes,
            patch_scope=args.patch_scope,
            confirm_all_sync=args.confirm_all_sync
        )
        if success:
            print("[+] Sync completed successfully!")
        else:
            print("[!] Sync failed.")
            sys.exit(1)
    except Exception as e:
        print(f"[!] Error during synchronization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
