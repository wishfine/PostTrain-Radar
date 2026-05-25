import argparse
import sys
import os
import sqlite3
import yaml
import json

# Adjust Python path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app import PostTrainRadarApp

def get_candidates(venue: str, year: int, top_k: int):
    app = PostTrainRadarApp()
    papers = app.db.get_classified_papers(venue, year)
    
    # We consider papers that are candidates or classified as relevant
    candidate_papers = [p for p in papers if p.get("is_relevant") == 1 or p.get("is_candidate") == 1]
    
    # Custom sorting function
    def sort_key(p):
        is_a_core = 1 if (p.get("relevance_level") == "A_Core_PostTraining" or p.get("is_core_posttraining") == 1) else 0
        is_high = 1 if p.get("priority") == "High" else 0
        is_worth_sharing = 1 if (p.get("share_status") == "WorthSharing" or p.get("include_in_share_pool") == 1) else 0
        conf = p.get("confidence", 0.0)
        method_relevance = len(p.get("post_training_types", []))
        
        # Invert to sort in descending order
        return (-is_a_core, -is_high, -is_worth_sharing, -conf, -method_relevance)
        
    candidate_papers.sort(key=sort_key)
    return candidate_papers[:top_k]

def main():
    parser = argparse.ArgumentParser(description="Generate YAML draft of override candidates.")
    parser.add_argument("--venue", type=str, default="ICLR", help="Target conference venue, e.g. ICLR")
    parser.add_argument("--year", type=int, default=2025, help="Target conference year, e.g. 2025")
    parser.add_argument("--top-k", type=int, default=50, help="Number of candidates to generate")
    args = parser.parse_args()
    
    print(f"[*] Generating top {args.top_k} overrides candidates for {args.venue} {args.year}...")
    candidates = get_candidates(args.venue, args.year, args.top_k)
    
    if not candidates:
        print(f"[-] No relevant papers found in database for {args.venue} {args.year}.")
        sys.exit(0)
        
    out_dict = {}
    for p in candidates:
        # Use source_id as primary key if available, otherwise title_norm
        key = p.get("source_id")
        if not key or str(key).strip() == "":
            key = p.get("title_norm")
            
        evidence = p.get("matched_evidence", {})
        evidence_str = ""
        if isinstance(evidence, dict):
            # Format evidence list to a brief summary
            summary = []
            for sect, items in evidence.items():
                if items:
                    summary.append(f"{sect}: {items}")
            evidence_str = "; ".join(summary)
        else:
            evidence_str = str(evidence)
            
        out_dict[key] = {
            "title": p.get("title"),
            "source_id": p.get("source_id"),
            "venue": p.get("venue"),
            "year": p.get("year"),
            "relevance_level": p.get("relevance_level"),
            "priority": p.get("priority", "Medium"),
            "confidence": p.get("confidence", 0.0),
            "model_type": p.get("model_type"),
            "method_tags": p.get("post_training_types", []),
            "problem_tags": p.get("problem_tags", []),
            "matched_evidence": evidence_str,
            "reviewer_comment": p.get("reviewer_comment", ""),
            "next_action": p.get("next_action", ""),
            # Five false control switches
            "manual_selected": False,
            "include_in_siyuan": False,
            "include_in_reading_queue": False,
            "include_in_knowledge_patches": False,
            "include_in_share_pool": False
        }
        
    os.makedirs("data/manual", exist_ok=True)
    out_path = f"data/manual/tag_overrides_candidates_{args.venue.lower()}_{args.year}.yaml"
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Top {args.top_k} Candidates for {args.venue} {args.year}\n")
        f.write("# Review and change values to true, then copy entries to tag_overrides.yaml\n\n")
        yaml.dump(out_dict, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
    print(f"[+] Successfully generated override candidates to: {out_path}")

if __name__ == "__main__":
    main()
