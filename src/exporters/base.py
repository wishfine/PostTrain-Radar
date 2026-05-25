from abc import ABC, abstractmethod

class BaseExporter(ABC):
    @abstractmethod
    def export_paper_note(self, paper: dict, markdown_content: str, overwrite: bool = False) -> bool:
        """
        Exports the paper reading note.
        """
        pass

    @abstractmethod
    def export_report(self, report_name: str, markdown_content: str, overwrite: bool = False) -> bool:
        """
        Exports the conference report.
        """
        pass

    @abstractmethod
    def export_report_at_path(self, target_path: str, markdown_content: str, overwrite: bool = False) -> bool:
        """
        Exports a report or list at a specific path.
        """
        pass

    @abstractmethod
    def export_share_brief(self, paper: dict, markdown_content: str, overwrite: bool = False) -> bool:
        """
        Exports the paper share brief.
        """
        pass

    @abstractmethod
    def export_workflow_prompts(self, prompt_name: str, markdown_content: str, overwrite: bool = False) -> bool:
        """
        Exports the workflow prompts.
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Tests the endpoint/local path connection.
        """
        pass
