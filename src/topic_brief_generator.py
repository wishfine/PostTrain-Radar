import os

class TopicBriefGenerator:
    def generate(self, topic: str, papers: list) -> str:
        """
        Generates a topic-level group meeting seminar outline based on multiple papers.
        """
        # Filter papers matching the topic in post_training_types
        topic_papers = []
        for p in papers:
            # Check matching in post_training_types (case-insensitive substring check)
            if any(topic.lower() in t.lower() for t in p.get("post_training_types", [])):
                topic_papers.append(p)

        if not topic_papers:
            return f"# Topic Seminar: {topic}\n\n*No papers found matching this topic.*"

        paper_bullets = []
        for idx, p in enumerate(topic_papers, 1):
            authors_str = ", ".join(p.get("authors", []))
            paper_bullets.append(
                f"{idx}. **{p.get('title')}** ({p.get('venue')} {p.get('year')})\n"
                f"   - *Authors*: {authors_str}\n"
                f"   - *Model Type*: {p.get('model_type')}\n"
                f"   - *Confidence*: {p.get('confidence')}\n"
                f"   - *URL*: {p.get('paper_url') or 'N/A'}"
            )
        paper_bullets_str = "\n".join(paper_bullets)

        methods_summary = []
        problems_summary = []
        for p in topic_papers:
            methods_summary.extend(p.get("post_training_types", []))
            problems_summary.extend(p.get("problem_tags", []))
        
        methods_summary = list(set(methods_summary))
        problems_summary = list(set(problems_summary))

        outline = f"""# Topic Seminar: {topic} Group Meeting Outline

## 📅 Agenda & Focus
This seminar reviews {len(topic_papers)} papers regarding the **{topic}** methodology in LLM/VLM Post-Training.

### 🔬 Core Methods Discussed
- {chr(10).join(['- ' + m for m in methods_summary]) if methods_summary else 'No methods tagged.'}

### ⚠️ Problems Addressed
- {chr(10).join(['- ' + p for p in problems_summary]) if problems_summary else 'No problems tagged.'}

---

## 📚 Key Papers Selected
{paper_bullets_str}

---

## 🗺️ Presentation Outline (60-Minute Seminar Layout)

### 1. Introduction & Context (10 Mins)
- **The Core Problem**: Why do we need this technology? (SFT limitations, alignment difficulties).
- **The Evolution**: How does this fit in the general post-training timeline (from standard PPO to current methods)?

### 2. Method Comparison & Analysis (25 Mins)
- **Mathematical Formulations**: Contrast the loss functions or rule-based feedback setups across the selected papers.
- **Key Innovators**:
  - What does each paper assume?
  - What are the major reference model or critic changes?
- **Engineering / Implementation Trades**: Contrast compute requirements, GPU memory savings, and dataset reliance.

### 3. Experimental Review & Synthesis (15 Mins)
- **Benchmark Performance**: Where do these papers show the most significant gains (e.g. AlpacaEval, MT-Bench, GSM8K)?
- **Ablation Studies**: What do the ablation experiments reveal about the core parameters (e.g., beta in DPO, group size in GRPO)?
- **Identified Limitations**: Discuss length bias, model collapse, or task generalization compromises.

### 4. Group Brainstorming & Next Steps (10 Mins)
- **Relevance to Our Research**: How can we apply or transfer these findings to our active tasks?
- **Suggested Discussion Questions**:
  1. *Do these offline optimization methods scale well compared to online reinforcement learning as parameters increase?*
  2. *How can we design more reliable verification systems to mitigate reward hacking in multi-modal environments?*
  3. *Can we design a hybrid approach combining the best elements of these papers?*
"""
        return outline
