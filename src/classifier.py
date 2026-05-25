import os
import yaml
import json
from src.normalizer import normalize_title

class BaseClassifier:
    def classify(self, title: str, abstract: str, source_id: str = None) -> dict:
        raise NotImplementedError

class RuleClassifier(BaseClassifier):
    def __init__(self, config_path="config/categories.yaml", overrides_path="data/manual/tag_overrides.yaml"):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Categories config not found at: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        self.overrides_path = overrides_path
        self.overrides = {}
        self._load_overrides()

    def _load_overrides(self):
        if os.path.exists(self.overrides_path):
            try:
                with open(self.overrides_path, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if isinstance(content, dict):
                        for k, v in content.items():
                            if isinstance(v, dict):
                                self.overrides[str(k).lower().strip()] = v
                print(f"[+] Loaded {len(self.overrides)} manual tag overrides.")
            except Exception as e:
                print(f"[!] Warning: Failed to load overrides file: {e}")

    def classify(self, title: str, abstract: str, source_id: str = None) -> dict:
        title_lower = (title or "").lower()
        abstract_lower = (abstract or "").lower()
        combined = f"{title_lower} {abstract_lower}"

        # Initialize evidence logs
        matched_evidence = {
            "model_type": {},
            "post_training_types": {},
            "problem_tags": {}
        }

        # 1. Classify Model Type
        model_type = "LLM"  # Default
        model_rules = {
            "Video-LMM": ["video-lmm", "video language", "long video", "video understanding"],
            "VLM": ["vision-language", "vlm", "multimodal", "mllm", "lvlm", "image", "visual"],
            "Reward Model": ["reward model", "reward modeling", "prm", "orm"],
            "Agent": ["agent", "tool-use", "multi-agent", "sandbox", "action"]
        }

        for m_type, keywords in model_rules.items():
            matched = [kw for kw in keywords if kw in combined]
            if matched:
                model_type = m_type
                matched_evidence["model_type"][m_type] = matched
                break  # Pick first matched model type

        # 2. Classify Post-Training Methods
        post_training_types = []
        method_map = {
            "SFT / Instruction Tuning": ["sft", "supervised fine-tuning", "instruction tuning", "instruction-tuned", "instruction micro-tuning"],
            "RLHF / PPO": ["rlhf", "ppo", "reinforcement learning from human feedback", "policy gradient"],
            "RLAIF": ["rlaif", "reinforcement learning from ai feedback", "ai feedback"],
            "DPO / Preference Optimization": ["dpo", "direct preference optimization", "ipo", "kto", "orpo", "simpo", "preference optimization", "offline alignment"],
            "GRPO / Reasoning RL": ["grpo", "group relative policy optimization", "reasoning rl", "reasoning model", "math reasoning", "code reasoning", "chain of thought", "long-cot", "reasoning capability"],
            "Reward Modeling": ["reward model", "reward modeling", "preference model"],
            "Process Reward Model": ["process reward", "prm", "step-level", "step by step verifier"],
            "Outcome Reward Model": ["outcome reward", "orm", "sequence-level reward"],
            "Verifier / Critic": ["verifier", "critic", "validator"],
            "Test-Time Scaling": ["test-time", "test time", "search-based", "best-of-n", "mcts", "monte carlo tree search", "beam search"],
            "Self-Improvement": ["self-improvement", "self-correction", "self-training", "self-play"],
            "Multimodal Alignment": ["multimodal alignment", "cross-modal alignment", "modality alignment"],
            "Visual Instruction Tuning": ["visual instruction", "multimodal instruction", "vl-instruction"],
            "Multimodal Preference Optimization": ["multimodal preference", "visual preference", "vlm dpo"],
            "Safety Alignment": ["safety", "jailbreak", "red-teaming", "toxic", "guardrail"],
            "Data Selection / Data Quality": ["data selection", "data quality", "pruning", "data filtering", "curation"],
            "Evaluation / Benchmark": ["evaluation", "benchmark", "dataset", "test suite"]
        }

        for method, keywords in method_map.items():
            matched = [kw for kw in keywords if kw in combined]
            if matched:
                post_training_types.append(method)
                matched_evidence["post_training_types"][method] = matched

        # 3. Classify Problem Tags
        problem_tags = []
        problem_map = {
            "Reward Hacking": ["reward hacking", "reward exploitation", "gaming", "reward hack", "policy cheat"],
            "Length Bias": ["length bias", "verbosity", "longer answers", "sentence length bias", "verbose answer"],
            "Credit Assignment": ["credit assignment", "token-level credit", "reward distribution", "sparse feedback"],
            "Preference Data Distribution Shift": ["distribution shift", "out-of-distribution", "off-policy", "ood"],
            "Reward Model Overfitting": ["reward model overfit", "rm overfitting", "reward model degradation"],
            "Evaluation Leakage": ["leakage", "contamination", "test set leak"],
            "Multimodal Hallucination": ["hallucination", "hallucinate", "visual hallucination"],
            "Visual Grounding Failure": ["grounding", "visual grounding", "spatial reasoning", "bounding box"],
            "Tool-use Credit Assignment": ["tool-use", "tool calling", "api call credit"],
            "Test-time Compute Cost": ["compute cost", "latency", "search compute", "computational budget"],
            "Data Quality": ["data quality", "noise", "cleaning", "label noise", "corrupted label"]
        }

        for prob, keywords in problem_map.items():
            matched = [kw for kw in keywords if kw in combined]
            if matched:
                problem_tags.append(prob)
                matched_evidence["problem_tags"][prob] = matched

        # 4. Calculate Confidence Score
        confidence = 0.5
        title_combined = title_lower
        if any(kw in title_combined for kw in ["dpo", "grpo", "rlhf", "ppo", "sft", "instruction tuning"]):
            confidence += 0.25
        if any(kw in title_combined for kw in ["reward model", "verifier", "critic", "reasoning"]):
            confidence += 0.15
        if len(post_training_types) > 0:
            confidence += 0.1
        
        confidence = min(0.99, max(0.5, confidence))

        reason = f"Classified as model_type='{model_type}' based on context. Methods matched: {post_training_types}. Problems matched: {problem_tags}."

        res = {
            "is_relevant": 1 if len(post_training_types) > 0 else 0,
            "model_type": model_type,
            "post_training_types": post_training_types,
            "problem_tags": problem_tags,
            "confidence": round(confidence, 2),
            "reason": reason,
            "matched_evidence": matched_evidence
        }

        # Apply Overrides if present
        title_norm = normalize_title(title)
        override = None

        if source_id and str(source_id).lower().strip() in self.overrides:
            override = self.overrides[str(source_id).lower().strip()]
        elif title_norm in self.overrides:
            override = self.overrides[title_norm]

        if override:
            print(f"[*] Applying manual overrides for paper '{title}': {override}")
            for k, v in override.items():
                res[k] = v
            # Recalculate is_relevant
            if "post_training_types" in override:
                res["is_relevant"] = 1 if len(override["post_training_types"]) > 0 else 0

        return res

class LLMClassifier(BaseClassifier):
    def __init__(self, api_key=None, model="gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    def classify(self, title: str, abstract: str, source_id: str = None) -> dict:
        return RuleClassifier().classify(title, abstract, source_id)
