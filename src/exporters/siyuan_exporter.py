import os
import requests
import json
from src.exporters.base import BaseExporter
from src.exporters.markdown_exporter import safe_filename
from src.note_generator import NoteGenerator
from src.share_generator import ShareGenerator

class SiYuanExporter(BaseExporter):
    def __init__(self, api_url: str = "http://127.0.0.1:6806", 
                 token_env: str = "SIYUAN_TOKEN", 
                 notebook_name: str = "PostTrain Radar",
                 notebook_id: str = "",
                 dry_run=False):
        self.api_url = api_url.rstrip("/")
        self.token = os.getenv(token_env, "")
        self.notebook_name = notebook_name
        self.notebook_id = notebook_id
        self.dry_run = dry_run
        self.note_gen = NoteGenerator()
        self.share_gen = ShareGenerator()

    def _call_api(self, endpoint: str, data: dict) -> dict:
        url = f"{self.api_url}{endpoint}"
        headers = {
            "Content-Type": "application/json"
        }
        if self.token:
            headers["Authorization"] = f"Token {self.token}"

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[!] Error calling SiYuan API {endpoint}: {e}")
            return None

    def test_connection(self) -> bool:
        if self.dry_run:
            print("[*] [DRY-RUN] Simulating SiYuan connection test: SUCCESS")
            return True
        if not self.token:
            print("[!] SIYUAN_TOKEN is not set in environment.")
            return False

        res = self._call_api("/api/system/version", {})
        if res and res.get("code") == 0:
            print(f"[+] Connected to SiYuan Note successfully (Version: {res.get('data')})")
            return True
        print("[!] Failed to connect to SiYuan Note API.")
        return False

    def validate_notebook(self) -> bool:
        """
        Validates the configured notebook_name or notebook_id.
        If target is not found, displays list of active notebooks and returns False.
        """
        if self.dry_run and not self.token:
            # Under dry run, if token is empty, mock it
            self.notebook_id = "mock_notebook_id"
            return True

        res = self._call_api("/api/notebook/lsNotebooks", {})
        if not res or res.get("code") != 0:
            print("[!] Failed to list notebooks from SiYuan API.")
            return False

        notebooks = res.get("data", {}).get("notebooks", [])
        
        # 1. Match by notebook_id
        if self.notebook_id:
            for nb in notebooks:
                if nb.get("id") == self.notebook_id:
                    self.notebook_name = nb.get("name")
                    return True
            print(f"[!] Notebook ID '{self.notebook_id}' was not found in SiYuan.")
            return False

        # 2. Match by notebook_name
        for nb in notebooks:
            if nb.get("name") == self.notebook_name:
                self.notebook_id = nb.get("id")
                print(f"[+] Found SiYuan notebook '{self.notebook_name}' (ID: {self.notebook_id})")
                return True

        # 3. If no match is found, raise error and display notebooks list
        print(f"[!] Target notebook '{self.notebook_name}' was not found in SiYuan.")
        if notebooks:
            print("Available notebooks in your SiYuan instance:")
            for nb in notebooks:
                print(f"  - {nb.get('name')} (ID: {nb.get('id')})")
        else:
            print("  (No notebooks found in your SiYuan instance)")
        return False

    def _find_doc_id_and_path(self, target_path_without_ext: str):
        """
        Helper to check if a document exists at target_path_without_ext.
        """
        if self.dry_run and not self.token:
            return None, None
            
        components = target_path_without_ext.strip("/").split("/")
        if not components:
            return None, None

        current_path = "/"
        current_id = None
        
        for comp in components:
            res = self._call_api("/api/filetree/listDocsByPath", {
                "notebook": self.notebook_id,
                "path": current_path
            })
            if not res or res.get("code") != 0:
                return None, None
                
            files = res.get("data", {}).get("files", [])
            found = False
            for f in files:
                name = f.get("name", "")
                if name.endswith(".sy"):
                    name = name[:-3]
                if name == comp:
                    current_id = f.get("id")
                    current_path = f.get("path")
                    if current_path.endswith(".sy"):
                        current_path = current_path[:-3]
                    found = True
                    break
            if not found:
                return None, None
                
        return current_id, current_path + ".sy" if not current_path.endswith(".sy") else current_path

    def export_paper_note(self, paper: dict, markdown_content: str, overwrite: bool = False) -> bool:
        if not self.notebook_id and not self.validate_notebook():
            return False

        source = paper.get("source", "").lower()
        status = paper.get("status", "").lower()
        
        venue = safe_filename(paper.get("venue", "unknown"))
        year = paper.get("year", 2025)
        title = safe_filename(paper.get("title", "untitled"))

        # Enforce V3 Routing Rules
        if source in ["openreview", "acl_anthology", "cvf_openaccess"] and status == "accepted":
            target_path = f"/01_Papers/{venue}_{year}/{title}"
        elif source == "arxiv":
            target_path = f"/01_Papers/ArXiv_Preprints/{title}"
        else:
            target_path = f"/01_Papers/Manual_Import/{title}"

        doc_id, doc_path = self._find_doc_id_and_path(target_path)

        if doc_id:
            # Document already exists, update in-place using updateBlock
            if not self.dry_run:
                get_res = self._call_api("/api/export/exportMdContent", {"id": doc_id})
                markdown_content = None
                if get_res and get_res.get("code") == 0:
                    old_content = get_res.get("data", {}).get("content", "")
                    markdown_content = self.note_gen.generate(paper, old_content, overwrite=overwrite)
                
                if markdown_content is None:
                    print(f"[!] WARNING: Skipping update for paper note '{title}' because protected sections were missing in the existing document.")
                    return True

                update_res = self._call_api("/api/block/updateBlock", {
                    "id": doc_id,
                    "dataType": "markdown",
                    "data": markdown_content
                })
                if update_res and update_res.get("code") == 0:
                    print(f"[+] Updated paper note in place in SiYuan: {target_path} (ID: {doc_id})")
                    paper["siyuan_doc_id"] = doc_id
                    paper["siyuan_path"] = doc_path
                    return True
                else:
                    print(f"[!] Failed to update paper note in SiYuan: {update_res}")
                    return False
            else:
                print(f"[*] [DRY-RUN] Would UPDATE SiYuan paper note in place at path: {target_path} (ID: {doc_id})")
                paper["siyuan_doc_id"] = doc_id
                paper["siyuan_path"] = doc_path
                return True

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would CREATE SiYuan paper note at path: {target_path}")
            paper["siyuan_doc_id"] = "dry_run_mock_doc_id"
            paper["siyuan_path"] = f"{target_path}.sy"
            return True

        create_res = self._call_api("/api/filetree/createDocWithMd", {
            "notebook": self.notebook_id,
            "path": target_path,
            "markdown": markdown_content
        })

        if create_res and create_res.get("code") == 0:
            new_id = create_res.get("data")
            new_path = f"{target_path}.sy"
            print(f"[+] Synced paper note to SiYuan: {target_path} (ID: {new_id})")
            paper["siyuan_doc_id"] = new_id
            paper["siyuan_path"] = new_path
            return True
        else:
            print(f"[!] Failed to sync paper note to SiYuan: {create_res}")
            return False

    def export_share_brief(self, paper: dict, markdown_content: str, overwrite: bool = False) -> bool:
        if not self.notebook_id and not self.validate_notebook():
            return False

        source = paper.get("source", "").lower()
        status = paper.get("status", "").lower()

        venue = safe_filename(paper.get("venue", "unknown")).upper()
        year = paper.get("year", 2025)
        title = safe_filename(paper.get("title", "untitled"))

        target_path = f"/05_Share/Group_Meeting/Paper_Briefs/{venue}_{year}/{title}_Share_Brief"

        doc_id, doc_path = self._find_doc_id_and_path(target_path)

        if doc_id:
            # Document exists, update in-place using updateBlock
            if not self.dry_run:
                get_res = self._call_api("/api/export/exportMdContent", {"id": doc_id})
                if get_res and get_res.get("code") == 0:
                    old_content = get_res.get("data", {}).get("content", "")
                    markdown_content = self.share_gen.generate(paper, old_content)
                
                update_res = self._call_api("/api/block/updateBlock", {
                    "id": doc_id,
                    "dataType": "markdown",
                    "data": markdown_content
                })
                if update_res and update_res.get("code") == 0:
                    print(f"[+] Updated share brief in place in SiYuan: {target_path} (ID: {doc_id})")
                    return True
                else:
                    print(f"[!] Failed to update share brief in SiYuan: {update_res}")
                    return False
            else:
                print(f"[*] [DRY-RUN] Would UPDATE share brief in place in SiYuan: {target_path} (ID: {doc_id})")
                return True

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would CREATE SiYuan share brief at path: {target_path}")
            return True

        create_res = self._call_api("/api/filetree/createDocWithMd", {
            "notebook": self.notebook_id,
            "path": target_path,
            "markdown": markdown_content
        })

        if create_res and create_res.get("code") == 0:
            print(f"[+] Synced share brief to SiYuan: {target_path}")
            return True
        else:
            print(f"[!] Failed to sync share brief to SiYuan: {create_res}")
            return False

    def export_report(self, report_name: str, markdown_content: str, overwrite: bool = False) -> bool:
        if not self.notebook_id and not self.validate_notebook():
            return False

        report_name = safe_filename(report_name)
        target_path = f"/00_Index/{report_name}"
        doc_id, doc_path = self._find_doc_id_and_path(target_path)

        if doc_id:
            if not overwrite:
                print(f"[-] SiYuan report '{report_name}' already exists. Action: SKIP.")
                return True
            else:
                if not self.dry_run:
                    update_res = self._call_api("/api/block/updateBlock", {
                        "id": doc_id,
                        "dataType": "markdown",
                        "data": markdown_content
                    })
                    if update_res and update_res.get("code") == 0:
                        print(f"[+] Updated report in place in SiYuan: {target_path} (ID: {doc_id})")
                        return True
                    else:
                        print(f"[!] Failed to update report: {update_res}")
                        return False
                else:
                    print(f"[*] [DRY-RUN] Would UPDATE SiYuan report in place at path: {target_path} (ID: {doc_id})")
                    return True

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would CREATE SiYuan report at path: {target_path}")
            return True

        create_res = self._call_api("/api/filetree/createDocWithMd", {
            "notebook": self.notebook_id,
            "path": target_path,
            "markdown": markdown_content
        })

        if create_res and create_res.get("code") == 0:
            print(f"[+] Synced report to SiYuan: {target_path}")
            return True
        else:
            print(f"[!] Failed to sync report to SiYuan: {create_res}")
            return False

    def export_report_at_path(self, target_path: str, markdown_content: str, overwrite: bool = False) -> bool:
        """
        Special helper to write report at exact path.
        """
        if not self.notebook_id and not self.validate_notebook():
            return False

        doc_id, doc_path = self._find_doc_id_and_path(target_path)
        if doc_id:
            if not overwrite:
                return True
            else:
                if not self.dry_run:
                    update_res = self._call_api("/api/block/updateBlock", {
                        "id": doc_id,
                        "dataType": "markdown",
                        "data": markdown_content
                    })
                    return update_res and update_res.get("code") == 0
                else:
                    print(f"[*] [DRY-RUN] Would UPDATE SiYuan document in place at path: {target_path} (ID: {doc_id})")
                    return True

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would CREATE SiYuan document at path: {target_path}")
            return True

        create_res = self._call_api("/api/filetree/createDocWithMd", {
            "notebook": self.notebook_id,
            "path": target_path,
            "markdown": markdown_content
        })
        return create_res and create_res.get("code") == 0

    def export_workflow_prompts(self, prompt_name: str, markdown_content: str, overwrite: bool = False) -> bool:
        if not self.notebook_id and not self.validate_notebook():
            return False

        prompt_name = safe_filename(prompt_name)
        target_path = f"/06_Workflows/Prompts/{prompt_name}"
        doc_id, doc_path = self._find_doc_id_and_path(target_path)

        if doc_id:
            if not overwrite:
                print(f"[-] Workflow prompt '{prompt_name}' already exists in SiYuan. Action: SKIP (overwrite=False).")
                return True
            else:
                if not self.dry_run:
                    update_res = self._call_api("/api/block/updateBlock", {
                        "id": doc_id,
                        "dataType": "markdown",
                        "data": markdown_content
                    })
                    return update_res and update_res.get("code") == 0
                else:
                    print(f"[*] [DRY-RUN] Would UPDATE workflow prompt template in place at path: {target_path} (ID: {doc_id})")
                    return True

        if self.dry_run:
            print(f"[*] [DRY-RUN] Would CREATE workflow prompt to SiYuan at path: {target_path}")
            return True

        create_res = self._call_api("/api/filetree/createDocWithMd", {
            "notebook": self.notebook_id,
            "path": target_path,
            "markdown": markdown_content
        })

        if create_res and create_res.get("code") == 0:
            print(f"[+] Synced workflow prompt to SiYuan: {target_path}")
            return True
        else:
            print(f"[!] Failed to sync workflow prompt to SiYuan: {create_res}")
            return False
