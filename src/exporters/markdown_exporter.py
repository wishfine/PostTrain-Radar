import os
import re
from src.exporters.base import BaseExporter
from src.note_generator import NoteGenerator
from src.share_generator import ShareGenerator

def safe_filename(name: str) -> str:
    """
    Remove invalid characters from filenames.
    """
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    cleaned = re.sub(r'\s+', " ", cleaned)
    return cleaned.strip()

class MarkdownExporter(BaseExporter):
    def __init__(self, output_dir="data", dry_run=False):
        self.output_dir = output_dir
        self.dry_run = dry_run
        self.note_gen = NoteGenerator()
        self.share_gen = ShareGenerator()

    def test_connection(self) -> bool:
        if self.dry_run:
            print("[*] [DRY-RUN] Simulating connection test: SUCCESS")
            return True
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            return True
        except Exception:
            return False

    def export_paper_note(self, paper: dict, markdown_content: str, overwrite: bool = False) -> bool:
        venue = safe_filename(paper.get("venue", "unknown"))
        year = paper.get("year", 2025)
        title = safe_filename(paper.get("title", "untitled"))
        
        dir_path = os.path.join(self.output_dir, "reading_notes", f"{venue}_{year}")
        file_path = os.path.join(dir_path, f"{title}.md")

        action = "CREATE"
        if os.path.exists(file_path):
            if not overwrite:
                print(f"[-] Paper note '{title}' already exists. Action: SKIP (use --overwrite to force update).")
                return True
            else:
                action = "MERGE & UPDATE"
                if not self.dry_run:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            old_content = f.read()
                        markdown_content = self.note_gen.generate(paper, old_content)
                    except Exception as e:
                        print(f"[!] Error reading old paper note for merge: {e}. Writing fresh copy.")
                    
                    if markdown_content is None:
                        print(f"[!] WARNING: Skipping update for paper note '{title}' because protected sections were missing in the existing document.")
                        return True

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would {action} paper note at: {file_path}")
            return True

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"[+] Saved paper note to {file_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to save paper note: {e}")
            return False

    def export_share_brief(self, paper: dict, markdown_content: str, overwrite: bool = False) -> bool:
        venue = safe_filename(paper.get("venue", "unknown"))
        year = paper.get("year", 2025)
        title = safe_filename(paper.get("title", "untitled"))

        dir_path = os.path.join(self.output_dir, "share_briefs", f"{venue}_{year}")
        file_path = os.path.join(dir_path, f"{title}_Share_Brief.md")

        action = "CREATE"
        if os.path.exists(file_path):
            if not overwrite:
                print(f"[-] Share brief for '{title}' already exists. Action: SKIP (use --overwrite to force update).")
                return True
            else:
                action = "MERGE & UPDATE"
                if not self.dry_run:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            old_content = f.read()
                        markdown_content = self.share_gen.generate(paper, old_content)
                    except Exception as e:
                        print(f"[!] Error reading old share brief for merge: {e}. Writing fresh copy.")

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would {action} share brief at: {file_path}")
            return True

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"[+] Saved share brief to {file_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to save share brief: {e}")
            return False

    def export_report(self, report_name: str, markdown_content: str, overwrite: bool = False) -> bool:
        report_name = safe_filename(report_name)
        dir_path = os.path.join(self.output_dir, "reports")
        file_path = os.path.join(dir_path, f"{report_name}.md")

        action = "CREATE"
        if os.path.exists(file_path):
            if not overwrite:
                print(f"[-] Report '{report_name}' already exists. Action: SKIP.")
                return True
            else:
                action = "OVERWRITE"

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would {action} report at: {file_path}")
            return True

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"[+] Saved report to {file_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to save report: {e}")
            return False

    def export_workflow_prompts(self, prompt_name: str, markdown_content: str, overwrite: bool = False) -> bool:
        prompt_name = safe_filename(prompt_name)
        dir_path = os.path.join(self.output_dir, "workflows", "prompts")
        file_path = os.path.join(dir_path, f"{prompt_name}.md")

        if os.path.exists(file_path) and not overwrite:
            return True

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would sync workflow prompt at: {file_path}")
            return True

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"[+] Saved prompt template to {file_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to save prompt template: {e}")
            return False

    def export_report_at_path(self, target_path: str, markdown_content: str, overwrite: bool = False) -> bool:
        components = [safe_filename(c) for c in target_path.strip("/").split("/")]
        file_path = os.path.join(self.output_dir, *components) + ".md"
        dir_path = os.path.dirname(file_path)

        action = "CREATE"
        if os.path.exists(file_path):
            if not overwrite:
                return True
            else:
                action = "OVERWRITE"

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would {action} report at path: {file_path}")
            return True

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"[+] Saved report at path: {file_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to save report at path: {e}")
            return False
