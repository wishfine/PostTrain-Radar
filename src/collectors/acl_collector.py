import warnings
from src.collectors import BaseCollector

class ACLCollector(BaseCollector):
    def collect(self, venue: str, year: int) -> list:
        warnings.warn(
            f"ACL Anthology collector for {venue} {year} is a skeletal implementation in v0.1. "
            "Please use OpenReview for stable metadata collection.",
            UserWarning
        )
        print(f"[!] ACL Anthology collector is under development for {venue} {year}. Returning empty list.")
        return []
