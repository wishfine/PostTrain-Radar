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
            overwrite=args.overwrite
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
