import os
import re
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

        # Initialize evidence logs in structured format
        matched_evidence = {
            "model_type": [],
            "post_training_types": [],
            "problem_tags": [],
            "false_positives": []
        }

        def find_matches(keywords, t_text, a_text):
            t_m = []
            a_m = []
            for kw in keywords:
                if len(kw) <= 5:
                    pattern = r'\b' + re.escape(kw) + r'\b'
                    if re.search(pattern, t_text):
                        t_m.append(kw)
                    if re.search(pattern, a_text):
                        a_m.append(kw)
                else:
                    if kw in t_text:
                        t_m.append(kw)
                    if kw in a_text:
                        a_m.append(kw)
            return t_m, a_m

        # 1. Classify Model Type
        model_type = "LLM"  # Default
        model_rules = {
            "Video-LMM": ["video-lmm", "video language", "long video", "video understanding"],
            "VLM": ["vision-language", "vlm", "multimodal", "mllm", "lvlm", "image", "visual"],
            "Reward Model": ["reward model", "reward modeling", "prm", "orm"],
            "Agent": ["agent", "tool-use", "multi-agent", "sandbox", "action"]
        }

        for m_type, keywords in model_rules.items():
            t_m, a_m = find_matches(keywords, title_lower, abstract_lower)
            if t_m or a_m:
                model_type = m_type
                matched_evidence["model_type"].append({
                    "keyword_group": m_type,
                    "title_matches": t_m,
                    "abstract_matches": a_m,
                    "reason_text": f"Matched model type keywords: {t_m or a_m}"
                })
                break

        # 2. Classify Post-Training Methods (A class vs B class)
        core_methods_map = {
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
            "Safety Alignment": ["safety", "jailbreak", "red-teaming", "toxic", "guardrail"]
        }

        related_methods_map = {
            "PEFT / LoRA": ["lora", "peft", "parameter-efficient", "adapter"],
            "Data Selection / Data Quality": ["data selection", "data quality", "pruning", "data filtering", "curation", "label noise", "noisy labels"],
            "Evaluation / Benchmark": ["evaluation", "benchmark", "dataset", "test suite"],
            "Model Editing": ["model editing", "knowledge editing"],
            "Activation Steering": ["activation steering", "representation engineering"],
            "Watermarking": ["watermark", "watermarking"],
            "Quantization": ["quantization", "quantized"],
            "Speculative Decoding": ["speculative decoding", "speculative sampling"]
        }

        post_training_types = []
        has_core = False
        has_related = False

        for method, keywords in core_methods_map.items():
            t_m, a_m = find_matches(keywords, title_lower, abstract_lower)
            if t_m or a_m:
                post_training_types.append(method)
                has_core = True
                matched_evidence["post_training_types"].append({
                    "keyword_group": method,
                    "title_matches": t_m,
                    "abstract_matches": a_m,
                    "reason_text": f"Matched core method keywords: {t_m or a_m}"
                })

        for method, keywords in related_methods_map.items():
            t_m, a_m = find_matches(keywords, title_lower, abstract_lower)
            if t_m or a_m:
                post_training_types.append(method)
                has_related = True
                matched_evidence["post_training_types"].append({
                    "keyword_group": method,
                    "title_matches": t_m,
                    "abstract_matches": a_m,
                    "reason_text": f"Matched related method keywords: {t_m or a_m}"
                })

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
            t_m, a_m = find_matches(keywords, title_lower, abstract_lower)
            if t_m or a_m:
                problem_tags.append(prob)
                matched_evidence["problem_tags"].append({
                    "keyword_group": prob,
                    "title_matches": t_m,
                    "abstract_matches": a_m,
                    "reason_text": f"Matched problem keywords: {t_m or a_m}"
                })

        # 4. Check False Positive triggers
        fp_reasons = []
        nlp_keywords = ["language model", "llm", "vlm", "transformer", "text", "translation", "dialogue", "prompt", "vocabulary", "token", "decoder", "encoder", "visual-language", "mllm", "multimodal", "gpt", "llama", "deepseek", "chat"]
        has_nlp = any(kw in title_lower or kw in abstract_lower for kw in nlp_keywords)

        # Generic RL
        rl_kws = ["reinforcement learning", "actor-critic", "ppo", "q-learning", "continuous control", "atari", "gridworld", "dqn"]
        has_rl = any(kw in title_lower or kw in abstract_lower for kw in rl_kws)
        if has_rl and not has_nlp:
            fp_reasons.append("generic RL task (no LLM/VLM context)")

        # Robot Policy
        robot_kws = ["robot", "robotic", "manipulation", "trajectory", "control policy", "motion planning", "imitation learning", "motor control"]
        has_robot = any(kw in title_lower or kw in abstract_lower for kw in robot_kws)
        if has_robot and not has_nlp:
            fp_reasons.append("robot policy (no LLM/VLM context)")

        # Representation Alignment
        rep_kws = ["representation alignment", "representation learning", "cross-modal retrieval", "contrastive learning", "feature alignment", "sentence embeddings"]
        has_rep = any(kw in title_lower or kw in abstract_lower for kw in rep_kws)
        if has_rep and not (has_core or has_nlp):
            fp_reasons.append("representation alignment without training context")

        # Non-LLM Reasoning
        reasoning_kws = ["formal reasoning", "logic solver", "satisfiability", "sat solver", "theorem prover", "knowledge graph reasoning"]
        has_reasoning = any(kw in title_lower or kw in abstract_lower for kw in reasoning_kws)
        if has_reasoning and not has_nlp:
            fp_reasons.append("non-LLM reasoning (no LLM context)")

        # Benchmark-only
        bench_kws = ["benchmark", "dataset", "test suite"]
        has_bench = any(kw in title_lower or kw in abstract_lower for kw in bench_kws)
        train_kws = ["sft", "dpo", "rlhf", "ppo", "grpo", "training", "fine-tune", "tuning", "align", "alignment", "policy", "learn", "learning", "optimize", "optimization", "adapt", "adaptation", "self-improve", "self-correction", "verifier", "critic", "scaling"]
        has_train = any(kw in title_lower or kw in abstract_lower for kw in train_kws)
        if has_bench and not has_train:
            fp_reasons.append("benchmark-only (no training/fine-tuning/alignment proposed)")

        if fp_reasons:
            matched_evidence["false_positives"] = fp_reasons

        # Determine Relevance Level
        if not has_nlp and not (has_core or has_related):
            relevance_level = "D_Irrelevant"
        elif fp_reasons:
            if has_core:
                relevance_level = "B_Related_LLM_VLM_Training_or_Evaluation"
            else:
                relevance_level = "C_General_LLM_VLM_Not_PostTraining"
        elif has_core:
            relevance_level = "A_Core_PostTraining"
        elif has_related:
            relevance_level = "B_Related_LLM_VLM_Training_or_Evaluation"
        elif has_nlp:
            relevance_level = "C_General_LLM_VLM_Not_PostTraining"
        else:
            relevance_level = "D_Irrelevant"

        is_relevant = 1 if relevance_level in ["A_Core_PostTraining", "B_Related_LLM_VLM_Training_or_Evaluation"] else 0
        is_core_posttraining = 1 if relevance_level == "A_Core_PostTraining" else 0

        # 5. Calculate Confidence Score
        confidence = 0.5
        if any(kw in title_lower for kw in ["dpo", "grpo", "rlhf", "ppo", "sft", "instruction tuning"]):
            confidence += 0.25
        if any(kw in title_lower for kw in ["reward model", "verifier", "critic", "reasoning"]):
            confidence += 0.15
        if len(post_training_types) > 0:
            confidence += 0.1
        confidence = min(0.99, max(0.5, confidence))

        reason = f"Classified as relevance_level='{relevance_level}' based on context. Methods matched: {post_training_types}. Problems matched: {problem_tags}."
        if fp_reasons:
            reason += f" Demoted due to: {', '.join(fp_reasons)}."

        res = {
            "is_relevant": is_relevant,
            "relevance_level": relevance_level,
            "is_core_posttraining": is_core_posttraining,
            "model_type": model_type,
            "post_training_types": post_training_types,
            "problem_tags": problem_tags,
            "confidence": round(confidence, 2),
            "reason": reason,
            "matched_evidence": matched_evidence,
            "include_in_reading_queue": 0,
            "include_in_knowledge_patches": 0,
            "include_in_share_pool": 0,
            "include_in_siyuan": 0,
            "manual_selected": 0,
            "reviewer_comment": ""
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
            if "relevance_level" in override:
                lvl = override["relevance_level"]
                res["is_core_posttraining"] = 1 if lvl == "A_Core_PostTraining" else 0
                res["is_relevant"] = 1 if lvl in ["A_Core_PostTraining", "B_Related_LLM_VLM_Training_or_Evaluation"] else 0
            if "is_core_posttraining" in override:
                res["is_core_posttraining"] = 1 if override["is_core_posttraining"] else 0
            if "is_relevant" in override:
                res["is_relevant"] = 1 if override["is_relevant"] else 0
            for extra in ["include_in_reading_queue", "include_in_knowledge_patches", "include_in_share_pool", "include_in_siyuan", "manual_selected", "reviewer_comment"]:
                if extra in override:
                    val = override[extra]
                    if isinstance(val, bool):
                        val = 1 if val else 0
                    res[extra] = val

        return res

class LLMClassifier(BaseClassifier):
    def __init__(self, api_key=None, model="gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    def classify(self, title: str, abstract: str, source_id: str = None) -> dict:
        return RuleClassifier().classify(title, abstract, source_id)
