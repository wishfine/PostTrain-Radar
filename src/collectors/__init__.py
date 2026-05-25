from abc import ABC, abstractmethod

class BaseCollector(ABC):
    @abstractmethod
    def collect(self, venue: str, year: int) -> list:
        """
        Collects raw paper metadata from a data source.
        Returns a list of dicts.
        """
        pass
