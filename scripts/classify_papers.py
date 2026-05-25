import os
import argparse
import pandas as pd
from src.app import PostTrainRadarApp

def main():
    parser = argparse.ArgumentParser(description="Classify candidate papers")
    parser.add_argument("--input", type=str, required=True, help="Input CSV path (e.g. data/processed/iclr_2025_candidates.csv)")
    parser.add_argument("--output", type=str, default="", help="Output CSV path (defaults to replacing _candidates.csv with _classified.csv)")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input CSV not found at: {input_path}")

    # Determine output path
    output_path = args.output
    if not output_path:
        dir_name = os.path.dirname(input_path)
        base_name = os.path.basename(input_path)
        if "_candidates.csv" in base_name:
            out_base = base_name.replace("_candidates.csv", "_classified.csv")
        else:
            out_base = "classified_" + base_name
        output_path = os.path.join(dir_name, out_base)

    # Instantiate app
    app = PostTrainRadarApp()

    # Read the input CSV
    print(f"[*] Reading candidate papers from {input_path}...")
    df = pd.read_csv(input_path)
    if df.empty:
        print("[!] Input CSV is empty. Writing empty classified CSV.")
        pd.DataFrame().to_csv(output_path, index=False)
        return

    classified_rows = []

    print("[*] Running rule-based classifier on candidate papers...")
    for idx, row in df.iterrows():
        source = row.get("source")
        source_id = row.get("source_id")
        
        cursor = app.db.conn.cursor()
        cursor.execute("SELECT id, title, abstract FROM papers WHERE source = ? AND source_id = ?", (source, source_id))
        db_row = cursor.fetchone()
        
        if db_row:
            p_id = db_row["id"]
            title = db_row["title"]
            abstract = db_row["abstract"]
            
            # Classify
            res = app.classifier.classify(title, abstract)
            
            # Save tagging details to database
            app.db.update_paper_tags(p_id, res)
            
            if res["is_relevant"]:
                # Fetch full tag + paper info to output
                # Let's run a query joining the paper and tag info
                cursor.execute("""
                    SELECT p.*, t.is_candidate, t.is_relevant, t.model_type, t.post_training_types,
                           t.problem_tags, t.keywords_matched, t.confidence, t.reason as classification_reason,
                           t.relevance_level, t.is_core_posttraining, t.include_in_reading_queue,
                           t.include_in_knowledge_patches, t.include_in_share_pool, t.reviewer_comment,
                           t.priority, t.reading_status, t.share_status, t.my_rating, t.next_action
                    FROM papers p
                    JOIN paper_tags t ON p.id = t.paper_id
                    WHERE p.id = ?
                """, (p_id,))
                class_info = dict(cursor.fetchone())
                classified_rows.append(class_info)
        else:
            print(f"[!] Warning: Paper '{row.get('title')}' not found in database. Skipping.")

    # Write classified CSV
    df_class = pd.DataFrame(classified_rows)
    if not df_class.empty and "authors" in df_class.columns:
        import json
        df_class["authors"] = df_class["authors"].apply(lambda x: ", ".join(json.loads(x)) if isinstance(x, str) and x.startswith("[") else x)

    df_class.to_csv(output_path, index=False)
    print(f"[+] Classification complete. Saved {len(classified_rows)} relevant papers to {output_path}")

if __name__ == "__main__":
    main()
