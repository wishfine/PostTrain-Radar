import os
import yaml

class KeywordFilter:
    def __init__(self, config_path="config/keywords.yaml"):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Keywords configuration file not found at: {config_path}")
            
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            
        self.llm_vlm_kws = [kw.lower().strip() for kw in config.get("llm_vlm_keywords", [])]
        
        # Merge general post-training and VLM specific post-training keywords
        post_train = config.get("post_training_keywords", [])
        vlm_post_train = config.get("vlm_post_training_keywords", [])
        self.post_train_kws = [kw.lower().strip() for kw in post_train + vlm_post_train]

    def check_paper(self, title: str, abstract: str):
        """
        Runs high-recall keyword filtering on the paper title and abstract.
        Returns:
            dict: {
                "is_candidate": bool,
                "keywords_matched": list[str],
                "candidate_reason": str
            }
        """
        title_text = (title or "").lower()
        abstract_text = (abstract or "").lower()
        combined_text = f"{title_text} {abstract_text}"

        matched_llm_vlm = []
        matched_post_train = []

        # Find matching LLM/VLM keywords
        for kw in self.llm_vlm_kws:
            if kw in combined_text:
                matched_llm_vlm.append(kw)

        # Find matching Post-Training keywords
        for kw in self.post_train_kws:
            if kw in combined_text:
                matched_post_train.append(kw)

        is_candidate = len(matched_llm_vlm) > 0 and len(matched_post_train) > 0
        keywords_matched = list(set(matched_llm_vlm + matched_post_train))

        if is_candidate:
            reason = (
                f"Matched LLM/VLM keywords: {matched_llm_vlm} "
                f"AND Post-Training keywords: {matched_post_train}"
            )
        else:
            reason = "Failed to match both LLM/VLM and Post-Training keywords."

        return {
            "is_candidate": is_candidate,
            "keywords_matched": keywords_matched,
            "candidate_reason": reason
        }
