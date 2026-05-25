import argparse
import sys
import os
from src.app import PostTrainRadarApp
from src.topic_brief_generator import TopicBriefGenerator
from src.exporters.markdown_exporter import safe_filename

def main():
    parser = argparse.ArgumentParser(description="Generate topic-level seminar outline from multiple papers")
    parser.add_argument("--topic", type=str, required=True, help="Topic name (e.g. DPO, GRPO, VLM Alignment)")
    parser.add_argument("--venue", type=str, default="ICLR", help="Target venue")
    parser.add_argument("--year", type=int, default=2025, help="Target year")
    parser.add_argument("--sync-target", type=str, default="markdown", choices=["markdown", "siyuan", "obsidian"], help="Sync target note software")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing seminar briefs")

    args = parser.parse_args()

    app = PostTrainRadarApp()
    papers = app.db.get_classified_papers(args.venue, args.year)

    if not papers:
        print(f"[!] No papers found in database for venue {args.venue} and year {args.year}.")
        sys.exit(1)

    generator = TopicBriefGenerator()
    brief_md = generator.generate(args.topic, papers)

    exporter = app.get_exporter(args.sync_target)
    if not exporter.test_connection():
        print(f"[!] Exporter connection failed for target: {args.sync_target}")
        sys.exit(1)

    # Determine sync path
    topic_filename = safe_filename(args.topic)
    
    if args.sync_target == "markdown":
        # Local output
        dir_path = "data/share_briefs/topics"
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, f"{topic_filename}_Seminar.md")
        if os.path.exists(file_path) and not args.overwrite:
            print(f"[-] Topic brief '{topic_filename}_Seminar' already exists. Skipping.")
            sys.exit(0)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(brief_md)
        print(f"[+] Saved topic seminar brief to {file_path}")
    else:
        # SiYuan or Obsidian
        # Target folder mapping is under 05_Share/Topics/
        target_path = f"/05_Share/Topics/{topic_filename}_Seminar"
        success = exporter.export_report_at_path(target_path, brief_md, overwrite=args.overwrite)
        if success:
            print(f"[+] Synced topic seminar brief to {args.sync_target} path: {target_path}")
        else:
            print(f"[!] Failed to sync topic brief.")
            sys.exit(1)

if __name__ == "__main__":
    main()
