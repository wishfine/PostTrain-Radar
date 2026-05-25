import os
from src.exporters.base import BaseExporter
from src.exporters.markdown_exporter import safe_filename
from src.note_generator import NoteGenerator
from src.share_generator import ShareGenerator

class ObsidianExporter(BaseExporter):
    def __init__(self, vault_path: str, root_dir: str = "PostTrain Radar", dry_run=False):
        self.vault_path = vault_path
        self.root_dir = root_dir
        self.dry_run = dry_run
        self.note_gen = NoteGenerator()
        self.share_gen = ShareGenerator()

    def _get_base_path(self):
        return os.path.join(self.vault_path, self.root_dir)

    def test_connection(self) -> bool:
        if self.dry_run:
            print("[*] [DRY-RUN] Simulating Obsidian connection test: SUCCESS")
            return True
        if not self.vault_path:
            print("[!] Obsidian vault path is empty.")
            return False
        if not os.path.exists(self.vault_path):
            print(f"[!] Obsidian vault path does not exist: {self.vault_path}")
            return False
        try:
            os.makedirs(self._get_base_path(), exist_ok=True)
            return True
        except Exception as e:
            print(f"[!] Failed to write to Obsidian vault path: {e}")
            return False

    def export_paper_note(self, paper: dict, markdown_content: str, overwrite: bool = False) -> bool:
        venue = safe_filename(paper.get("venue", "unknown"))
        year = paper.get("year", 2025)
        title = safe_filename(paper.get("title", "untitled"))

        dir_path = os.path.join(self._get_base_path(), "01_Papers", f"{venue}_{year}")
        file_path = os.path.join(dir_path, f"{title}.md")

        action = "CREATE"
        if os.path.exists(file_path):
            if not overwrite:
                print(f"[-] Obsidian note '{title}' already exists. Action: SKIP.")
                return True
            else:
                action = "MERGE & UPDATE"
                if not self.dry_run:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            old_content = f.read()
                        markdown_content = self.note_gen.generate(paper, old_content)
                    except Exception as e:
                        print(f"[!] Error merging Obsidian note: {e}")
                    
                    if markdown_content is None:
                        print(f"[!] WARNING: Skipping update for paper note '{title}' because protected sections were missing in the existing document.")
                        return True

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would {action} Obsidian note at: {file_path}")
            return True

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"[+] Synced paper note to Obsidian: {file_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to sync paper note to Obsidian: {e}")
            return False

    def export_share_brief(self, paper: dict, markdown_content: str, overwrite: bool = False) -> bool:
        venue = safe_filename(paper.get("venue", "unknown"))
        year = paper.get("year", 2025)
        title = safe_filename(paper.get("title", "untitled"))

        dir_path = os.path.join(self._get_base_path(), "05_Share", f"{venue}_{year}")
        file_path = os.path.join(dir_path, f"{title}_Share_Brief.md")

        action = "CREATE"
        if os.path.exists(file_path):
            if not overwrite:
                print(f"[-] Obsidian share brief '{title}' already exists. Action: SKIP.")
                return True
            else:
                action = "MERGE & UPDATE"
                if not self.dry_run:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            old_content = f.read()
                        markdown_content = self.share_gen.generate(paper, old_content)
                    except Exception as e:
                        print(f"[!] Error merging Obsidian share brief: {e}")

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would {action} Obsidian share brief at: {file_path}")
            return True

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"[+] Synced share brief to Obsidian: {file_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to sync share brief to Obsidian: {e}")
            return False

    def export_report(self, report_name: str, markdown_content: str, overwrite: bool = False) -> bool:
        report_name = safe_filename(report_name)
        dir_path = os.path.join(self._get_base_path(), "00_Index")
        file_path = os.path.join(dir_path, f"{report_name}.md")

        action = "CREATE"
        if os.path.exists(file_path):
            if not overwrite:
                print(f"[-] Obsidian report '{report_name}' already exists. Action: SKIP.")
                return True
            else:
                action = "OVERWRITE"

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would {action} Obsidian report at: {file_path}")
            return True

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"[+] Synced report to Obsidian: {file_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to sync report to Obsidian: {e}")
            return False

    def export_workflow_prompts(self, prompt_name: str, markdown_content: str, overwrite: bool = False) -> bool:
        prompt_name = safe_filename(prompt_name)
        dir_path = os.path.join(self._get_base_path(), "06_Workflows", "Prompts")
        file_path = os.path.join(dir_path, f"{prompt_name}.md")

        if os.path.exists(file_path) and not overwrite:
            return True

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would sync workflow prompt to Obsidian at: {file_path}")
            return True

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"[+] Synced workflow prompt to Obsidian: {file_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to sync workflow prompt to Obsidian: {e}")
            return False

    def export_report_at_path(self, target_path: str, markdown_content: str, overwrite: bool = False) -> bool:
        components = [safe_filename(c) for c in target_path.strip("/").split("/")]
        file_path = os.path.join(self._get_base_path(), *components) + ".md"
        dir_path = os.path.dirname(file_path)

        action = "CREATE"
        if os.path.exists(file_path):
            if not overwrite:
                return True
            else:
                action = "OVERWRITE"

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would {action} document to Obsidian at path: {file_path}")
            return True

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"[+] Synced document to Obsidian: {file_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to sync document to Obsidian: {e}")
            return False
