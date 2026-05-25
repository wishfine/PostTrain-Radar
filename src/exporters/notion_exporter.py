import warnings
from src.exporters.base import BaseExporter

class NotionExporter(BaseExporter):
    def test_connection(self) -> bool:
        print("[!] NotionExporter is not implemented in v0.1.")
        return False

    def export_paper_note(self, paper: dict, markdown_content: str, overwrite: bool = False) -> bool:
        warnings.warn("NotionExporter is a stub in v0.1. Export skipped.", UserWarning)
        return False

    def export_share_brief(self, paper: dict, markdown_content: str, overwrite: bool = False) -> bool:
        return False

    def export_report(self, report_name: str, markdown_content: str, overwrite: bool = False) -> bool:
        return False

    def export_workflow_prompts(self, prompt_name: str, markdown_content: str, overwrite: bool = False) -> bool:
        return False
