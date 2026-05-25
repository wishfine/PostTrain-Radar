import argparse
import warnings
from src.app import PostTrainRadarApp

def main():
    parser = argparse.ArgumentParser(description="Collect papers from ACL Anthology")
    parser.add_argument("--venue", type=str, default="ACL", help="Target venue")
    parser.add_argument("--year", type=int, default=2025, help="Target year")
    args = parser.parse_args()

    warnings.warn(
        "ACL Anthology collector is a skeletal stub in v0.1.",
        UserWarning
    )
    app = PostTrainRadarApp()
    app.run_collect(args.venue, args.year, "acl")

if __name__ == "__main__":
    main()
