import os
import argparse
import re
from src.app import PostTrainRadarApp
from src.exporters.markdown_exporter import safe_filename

def main():
    parser = argparse.ArgumentParser(description="Generate reading notes templates")
    parser.add_argument("--input", type=str, required=True, help="Input CSV path (e.g. data/processed/iclr_2025_classified.csv)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing notes (merges human segments)")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input CSV not found at: {input_path}")

    # Deduce venue/year
    base_name = os.path.basename(input_path).lower()
    match = re.search(r"([a-z]+)_(\d{4})", base_name)
    if match:
        venue = match.group(1).upper()
        year = int(match.group(2))
    else:
        venue = "ICLR"
        year = 2025

    app = PostTrainRadarApp()
    papers = app.db.get_classified_papers(venue, year)
    relevant_papers = [p for p in papers if p.get("is_relevant")]

    if not relevant_papers:
        print("[!] No relevant papers found to generate reading notes.")
        return

    exporter = app.get_exporter("markdown")
    count = 0
    for p in relevant_papers:
        note_md = app.note_gen.generate(p)
        success = exporter.export_paper_note(p, note_md, overwrite=args.overwrite)
        if success:
            count += 1
            
    print(f"[+] Finished generating reading notes. Synced {count} notes to data/reading_notes/")

if __name__ == "__main__":
    main()
