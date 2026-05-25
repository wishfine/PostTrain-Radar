import warnings
from src.collectors import BaseCollector

class CVFCollector(BaseCollector):
    def collect(self, venue: str, year: int) -> list:
        warnings.warn(
            f"CVF Open Access collector for {venue} {year} is a skeletal implementation in v0.1. "
            "Please use OpenReview for stable metadata collection.",
            UserWarning
        )
        print(f"[!] CVF Open Access collector is under development for {venue} {year}. Returning empty list.")
        return []
