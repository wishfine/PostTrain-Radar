import os
import json
import argparse
import pandas as pd
from src.app import PostTrainRadarApp
from src.exporters.markdown_exporter import safe_filename

def main():
    parser = argparse.ArgumentParser(description="Collect papers from OpenReview")
    parser.add_argument("--venue", type=str, default="ICLR", help="Target venue")
    parser.add_argument("--year", type=int, default=2025, help="Target year")
    args = parser.parse_args()

    venue_lower = safe_filename(args.venue.lower())
    year = args.year

    app = PostTrainRadarApp()
    
    # Run collection via app
    collector = app.get_collector("openreview")
    raw_papers = collector.collect(args.venue, year)

    # 1. Save raw JSON
    raw_dir = "data/raw"
    os.makedirs(raw_dir, exist_ok=True)
    raw_json_path = os.path.join(raw_dir, f"openreview_{venue_lower}_{year}.json")
    with open(raw_json_path, "w", encoding="utf-8") as f:
        json.dump(raw_papers, f, indent=2, ensure_ascii=False)
    print(f"[+] Saved raw JSON to {raw_json_path}")

    # 2. Insert into DB (to standardize schemas and deduplicate)
    saved_ids = app.run_collect(args.venue, year, "openreview")

    # 3. Save standardized processed CSV
    # Retrieve standardized records from DB
    papers_db = app.db.get_classified_papers(args.venue, year)
    
    processed_dir = "data/processed"
    os.makedirs(processed_dir, exist_ok=True)
    csv_path = os.path.join(processed_dir, f"{venue_lower}_{year}_papers.csv")
    
    df = pd.DataFrame(papers_db)
    # Ensure fields like authors are stringified for CSV storage
    if not df.empty and "authors" in df.columns:
        df["authors"] = df["authors"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
        
    df.to_csv(csv_path, index=False)
    print(f"[+] Saved processed papers CSV to {csv_path}")

if __name__ == "__main__":
    main()
