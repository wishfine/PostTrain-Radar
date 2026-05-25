import os
import argparse
import pandas as pd
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="Stratified sampling for post-classification quality audit")
    parser.add_argument("--input", type=str, required=True, help="Input classified CSV path (e.g. data/processed/iclr_2025_classified.csv)")
    parser.add_argument("--output-dir", type=str, default="data/audit", help="Output directory for audit files")
    parser.add_argument("--sample-per-priority", type=int, default=10, help="Number of papers to sample per priority stratum")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"Input file not found at: {args.input}")

    # Read the classified CSV
    df = pd.read_csv(args.input)
    if df.empty:
        print("[!] Input CSV is empty. Nothing to sample.")
        return

    # Standardize column priority values (High, Medium, Low)
    if "priority" not in df.columns:
        print("[!] Input CSV does not contain a 'priority' column. Cannot perform stratified sampling.")
        return

    df["priority"] = df["priority"].fillna("Medium").astype(str).str.capitalize()

    # Perform Stratified Sampling
    sampled_dfs = []
    for prio in ["High", "Medium", "Low"]:
        subset = df[df["priority"] == prio]
        n_available = len(subset)
        if n_available == 0:
            print(f"[-] Stratum '{prio}': 0 papers available. Skipping.")
            continue
        
        n_sample = min(n_available, args.sample_per_priority)
        print(f"[*] Stratum '{prio}': sampling {n_sample} out of {n_available} papers...")
        
        # Sample randomly
        sampled_subset = subset.sample(n=n_sample, random_state=42) # Fixed random state for reproducibility
        sampled_dfs.append(sampled_subset)

    if not sampled_dfs:
        print("[!] No papers sampled.")
        return

    df_sample = pd.concat(sampled_dfs, ignore_index=True)

    # 1. Output Manual Review CSV
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Try to deduce venue and year from filename to name output files
    base = os.path.basename(args.input)
    name_part = base.replace("_classified.csv", "")
    csv_out_path = os.path.join(args.output_dir, f"manual_review_{name_part}.csv")
    md_out_path = os.path.join(args.output_dir, f"audit_summary_{name_part}.md")

    # Add empty columns for reviewer
    df_review = df_sample.copy()
    df_review["reviewer_relevance_level"] = ""
    df_review["reviewer_is_core_posttraining"] = ""
    df_review["reviewer_priority"] = ""
    df_review["reviewer_comments"] = ""

    df_review.to_csv(csv_out_path, index=False)
    print(f"[+] Saved audit manual review template to: {csv_out_path}")

    # 2. Output Audit markdown
    md_lines = []
    md_lines.append(f"# Post-Classification Quality Audit Checklist: {name_part.upper().replace('_', ' ')}")
    md_lines.append("")
    md_lines.append(f"- **Total Sampled**: {len(df_sample)}")
    md_lines.append(f"- **Sample size per priority**: {args.sample_per_priority}")
    md_lines.append("- **Audit Protocol**:")
    md_lines.append("  1. Read the paper metadata, classification result, and abstract.")
    md_lines.append("  2. Fill in the review fields in the manual review CSV file.")
    md_lines.append("  3. Check for false positives: representation learning, robot policies, continuous control RL, benchmark-only, or non-LLM reasoning.")
    md_lines.append("")

    for prio in ["High", "Medium", "Low"]:
        prio_subset = df_sample[df_sample["priority"] == prio]
        if prio_subset.empty:
            continue
        
        md_lines.append(f"## {prio} Priority Stratum ({len(prio_subset)} papers)")
        md_lines.append("---")
        
        for idx, (_, row) in enumerate(prio_subset.iterrows(), 1):
            title = row.get("title", "Untitled")
            authors = row.get("authors", "Unknown")
            abstract = row.get("abstract", "")
            venue = row.get("venue", "Unknown")
            year = row.get("year", "Unknown")
            relevance_level = row.get("relevance_level", "Unknown")
            is_core = "Yes" if row.get("is_core_posttraining") == 1 else "No"
            model_type = row.get("model_type", "Other")
            post_train_str = row.get("post_training_types", "[]")
            problem_str = row.get("problem_tags", "[]")
            confidence = row.get("confidence", 0.0)
            reason = row.get("classification_reason", "")
            evidence = row.get("matched_evidence", "{}")
            
            md_lines.append(f"### {idx}. {title}")
            md_lines.append(f"- **Venue/Year**: {venue} {year}")
            md_lines.append(f"- **Authors**: {authors}")
            md_lines.append(f"- **Model Type**: {model_type}")
            md_lines.append(f"- **Post-Training Tag**: {post_train_str}")
            md_lines.append(f"- **Problem Tags**: {problem_str}")
            md_lines.append(f"- **Relevance Level**: `{relevance_level}` (Core Post-Training: **{is_core}**)")
            md_lines.append(f"- **Confidence Score**: `{confidence}`")
            md_lines.append(f"- **Heuristic Reason**: {reason}")
            md_lines.append(f"- **Evidence Matches**: `{evidence}`")
            md_lines.append("")
            md_lines.append("#### Abstract Summary:")
            md_lines.append(f"> {abstract}")
            md_lines.append("")
            md_lines.append("#### Review Checklist:")
            md_lines.append("- [ ] **Correct Relevance Level?** (A_Core / B_Related / C_General / D_Irrelevant)")
            md_lines.append("- [ ] **Correct Core Flag?** (Yes / No)")
            md_lines.append("- [ ] **Correct Priority Level?** (High / Medium / Low)")
            md_lines.append("- **Reviewer Comments**: ____________________________________________________")
            md_lines.append("")

    with open(md_out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
        
    print(f"[+] Saved audit summary markdown report to: {md_out_path}")

if __name__ == "__main__":
    main()
