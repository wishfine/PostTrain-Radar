import os
import argparse
import pandas as pd
from src.app import PostTrainRadarApp

def main():
    parser = argparse.ArgumentParser(description="Filter candidate papers by keywords")
    parser.add_argument("--input", type=str, required=True, help="Input CSV path (e.g. data/processed/iclr_2025_papers.csv)")
    parser.add_argument("--output", type=str, default="", help="Output CSV path (defaults to replacing _papers.csv with _candidates.csv)")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input CSV not found at: {input_path}")

    # Determine output path
    output_path = args.output
    if not output_path:
        dir_name = os.path.dirname(input_path)
        base_name = os.path.basename(input_path)
        if "_papers.csv" in base_name:
            out_base = base_name.replace("_papers.csv", "_candidates.csv")
        else:
            out_base = "candidates_" + base_name
        output_path = os.path.join(dir_name, out_base)

    # Instantiate app
    app = PostTrainRadarApp()

    # Read the input CSV
    print(f"[*] Reading papers from {input_path}...")
    df = pd.read_csv(input_path)
    if df.empty:
        print("[!] Input CSV is empty. Writing empty candidates CSV.")
        pd.DataFrame().to_csv(output_path, index=False)
        return

    # Find the corresponding IDs from database
    # In SQLite, we look up based on title_norm or source+source_id
    candidate_rows = []
    
    print("[*] Running keyword filter on papers...")
    for idx, row in df.iterrows():
        # Retrieve db record
        source = row.get("source")
        source_id = row.get("source_id")
        
        cursor = app.db.conn.cursor()
        cursor.execute("SELECT id, title, abstract FROM papers WHERE source = ? AND source_id = ?", (source, source_id))
        db_row = cursor.fetchone()
        
        if db_row:
            p_id = db_row["id"]
            title = db_row["title"]
            abstract = db_row["abstract"]
            
            # Filter
            res = app.filter.check_paper(title, abstract)
            
            # Save candidate flags to DB
            tag_data = {
                "is_candidate": 1 if res["is_candidate"] else 0,
                "keywords_matched": res["keywords_matched"],
                "reason": res["candidate_reason"]
            }
            app.db.update_paper_tags(p_id, tag_data)
            
            if res["is_candidate"]:
                # Fetch full tag + paper info to output
                cursor.execute("""
                    SELECT p.*, t.is_candidate, t.keywords_matched, t.reason as candidate_reason
                    FROM papers p
                    JOIN paper_tags t ON p.id = t.paper_id
                    WHERE p.id = ?
                """, (p_id,))
                cand_info = dict(cursor.fetchone())
                candidate_rows.append(cand_info)
        else:
            print(f"[!] Warning: Paper '{row.get('title')}' not found in database. Skipping.")

    # Write candidates CSV
    df_cand = pd.DataFrame(candidate_rows)
    if not df_cand.empty and "authors" in df_cand.columns:
        # Format list as string
        import json
        df_cand["authors"] = df_cand["authors"].apply(lambda x: ", ".join(json.loads(x)) if isinstance(x, str) and x.startswith("[") else x)

    df_cand.to_csv(output_path, index=False)
    print(f"[+] Screening complete. Saved {len(candidate_rows)} candidate papers to {output_path}")

if __name__ == "__main__":
    main()
