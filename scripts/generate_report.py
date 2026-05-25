import os
import argparse
import re
from src.app import PostTrainRadarApp
from src.reporter import ReportGenerator
from src.exporters.markdown_exporter import safe_filename

def main():
    parser = argparse.ArgumentParser(description="Generate conference markdown report")
    parser.add_argument("--input", type=str, required=True, help="Input CSV path (e.g. data/processed/iclr_2025_classified.csv)")
    parser.add_argument("--output-dir", type=str, default="data/reports", help="Output directory")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input CSV not found at: {input_path}")

    # Deduce venue and year from input filename e.g. "iclr_2025_classified.csv"
    base_name = os.path.basename(input_path).lower()
    match = re.search(r"([a-z]+)_(\d{4})", base_name)
    if match:
        venue = match.group(1).upper()
        year = int(match.group(2))
    else:
        venue = "ICLR"
        year = 2025

    print(f"[*] Deduced Venue: {venue}, Year: {year} from filename.")

    # Instantiate app and load classified papers for this venue/year from database
    app = PostTrainRadarApp()
    papers = app.db.get_classified_papers(venue, year)

    if not papers:
        print(f"[!] No papers found in database for venue {venue} and year {year}. Check database setup.")
        return

    # Generate Markdown Report
    reporter = ReportGenerator(venue, year)
    report_md = reporter.generate(papers)

    # Save to local reports folder
    os.makedirs(args.output_dir, exist_ok=True)
    out_filename = f"{venue.lower()}_{year}_posttrain_report"
    
    # Export using markdown exporter
    exporter = app.get_exporter("markdown")
    exporter.export_report(out_filename, report_md, overwrite=True)

if __name__ == "__main__":
    main()
