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
        "--siyuan-scope",
        type=str,
        default="selected",
        choices=["none", "index_only", "selected", "high", "core", "worth_sharing", "all"],
        help="Filter scope of papers to sync to SiYuan notes"
    )
    parser.add_argument(
        "--max-siyuan-notes",
        type=int,
        default=30,
        help="Maximum number of paper notes to sync to SiYuan (0 for unlimited)"
    )
    parser.add_argument(
        "--patch-scope",
        type=str,
        default="selected",
        choices=["selected", "high", "core", "all"],
        help="Scope of papers to generate knowledge patches for"
    )
    parser.add_argument(
        "--confirm-all-sync",
        action="store_true",
        help="Required confirmation flag if --siyuan-scope is 'all'"
    )
    parser.add_argument(
        "--skip-collect",
        action="store_true",
        help="Bypass online OpenReview scraping phase, loading existing papers from local SQLite instead"
    )
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Bypass collection, filtering, and classification entirely, executing a fast overrides application and sync"
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
            patch_scope=args.patch_scope,
            siyuan_scope=args.siyuan_scope,
            max_siyuan_notes=args.max_siyuan_notes,
            confirm_all_sync=args.confirm_all_sync,
            skip_collect=args.skip_collect,
            sync_only=args.sync_only
        )
    except Exception as e:
        import traceback
        import sys
        print("[!] Pipeline execution failed:")
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

if __name__ == "__main__":
    main()
