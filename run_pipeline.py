import argparse
import sys
from src.app import PostTrainRadarApp

def main():
    parser = argparse.ArgumentParser(
        description="PostTrain Radar - LLM/VLM Post-Training Paper Tracking & Sync Pipeline"
    )
    parser.add_argument(
        "--venue", 
        type=str, 
        default="ICLR", 
        help="Target conference venue (e.g. ICLR)"
    )
    parser.add_argument(
        "--year", 
        type=int, 
        default=2025, 
        help="Target conference year (e.g. 2025)"
    )
    parser.add_argument(
        "--source", 
        type=str, 
        default="openreview", 
        choices=["openreview", "acl", "cvf"], 
        help="Data collection source scraper"
    )
    parser.add_argument(
        "--sync-target", 
        type=str, 
        default="markdown", 
        choices=["markdown", "siyuan", "obsidian", "notion", "zotero"], 
        help="Note-taking software synchronization target"
    )
    parser.add_argument(
        "--overwrite", 
        action="store_true", 
        help="Enable to update existing notes (merging and preserving human text blocks)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline in simulation mode (no writes to filesystem/APIs/database runs)"
    )
    parser.add_argument(
        "--patch-scope",
        type=str,
        default="high",
        choices=["high", "selected", "all"],
        help="Scope of papers to generate knowledge patches for"
    )

    args = parser.parse_args()

    try:
        app = PostTrainRadarApp()
        app.run_pipeline(
            venue=args.venue,
            year=args.year,
            source_type=args.source,
            target_exporter=args.sync_target,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            patch_scope=args.patch_scope
        )
    except Exception as e:
        import traceback
        import sys
        print("[!] Pipeline execution failed:")
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

if __name__ == "__main__":
    main()
