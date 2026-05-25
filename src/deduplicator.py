from rapidfuzz import fuzz

class Deduplicator:
    def __init__(self, threshold=95.0):
        self.threshold = threshold

    def find_duplicate(self, paper_data, existing_papers):
        """
        Compare paper_data with list of existing paper dicts.
        Returns the existing duplicate paper dict if found, else None.
        """
        title_norm = paper_data.get("title_norm")
        if not title_norm:
            return None

        # 1. First Pass: Exact Match of Normalized Title
        for existing in existing_papers:
            if existing.get("title_norm") == title_norm:
                return existing

        # 2. Second Pass: Fuzzy Match of Normalized Title using RapidFuzz
        for existing in existing_papers:
            ex_title_norm = existing.get("title_norm")
            if not ex_title_norm:
                continue
            
            # Using token_sort_ratio is robust against word reordering
            score = fuzz.token_sort_ratio(title_norm, ex_title_norm)
            if score >= self.threshold:
                return existing

        return None
