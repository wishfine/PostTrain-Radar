import os
from collections import Counter

class ReportGenerator:
    def __init__(self, venue="ICLR", year=2025):
        self.venue = venue
        self.year = year

    def generate(self, papers: list) -> str:
        """
        Generates the Markdown report text from the list of papers.
        Each paper must be a dictionary representing the joined schema of papers & tags.
        """
        total_papers = len(papers)
        candidates = [p for p in papers if p.get("is_candidate")]
        candidate_count = len(candidates)
        
        relevant = [p for p in papers if p.get("is_relevant")]
        relevant_count = len(relevant)

        # Count category statistics
        category_counter = Counter()
        for p in relevant:
            for cat in p.get("post_training_types", []):
                category_counter[cat] += 1
            # Also count model types
            model_type = p.get("model_type")
            if model_type:
                category_counter[f"Model: {model_type}"] += 1

        # Sort category stats by count descending
        sorted_stats = sorted(category_counter.items(), key=lambda x: x[1], reverse=True)

        # Group papers by reading priority
        # High: confidence >= 0.80
        # Medium: 0.65 <= confidence < 0.80
        # Low: confidence < 0.65
        high_prio = []
        med_prio = []
        low_prio = []

        for p in relevant:
            conf = p.get("confidence", 0.5)
            if conf >= 0.80:
                high_prio.append(p)
            elif conf >= 0.65:
                med_prio.append(p)
            else:
                low_prio.append(p)

        # Sort priority groups by confidence descending
        high_prio = sorted(high_prio, key=lambda x: x.get("confidence", 0.0), reverse=True)
        med_prio = sorted(med_prio, key=lambda x: x.get("confidence", 0.0), reverse=True)
        low_prio = sorted(low_prio, key=lambda x: x.get("confidence", 0.0), reverse=True)

        # Construct Report
        lines = []
        lines.append(f"# PostTrain Radar Report: {self.venue} {self.year}")
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        lines.append(f"- Venue: {self.venue}")
        lines.append(f"- Year: {self.year}")
        lines.append(f"- Total papers: {total_papers}")
        lines.append(f"- Candidate papers: {candidate_count}")
        lines.append(f"- Relevant post-training papers: {relevant_count}")
        lines.append("")
        lines.append("## Category Statistics")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|---|---:|")
        if not sorted_stats:
            lines.append("| No relevant categories | 0 |")
        else:
            for cat, count in sorted_stats:
                lines.append(f"| {cat} | {count} |")
        lines.append("")
        lines.append("## Recommended Reading Priority")
        lines.append("")

        def format_paper_section(paper_list):
            if not paper_list:
                return "*None*\n"
            sec_lines = []
            for p in paper_list:
                sec_lines.append(f"### {p.get('title')}")
                sec_lines.append("")
                sec_lines.append(f"- Venue: {p.get('venue')}")
                sec_lines.append(f"- Year: {p.get('year')}")
                sec_lines.append(f"- Model Type: {p.get('model_type')}")
                sec_lines.append(f"- Post-training Type: {', '.join(p.get('post_training_types', []))}")
                sec_lines.append(f"- Problem Tags: {', '.join(p.get('problem_tags', []))}")
                sec_lines.append(f"- Confidence: {p.get('confidence')}")
                sec_lines.append(f"- Keywords: {', '.join(p.get('keywords_matched', []))}")
                sec_lines.append(f"- URL: {p.get('paper_url') or 'N/A'}")
                sec_lines.append(f"- PDF: {p.get('pdf_url') or 'N/A'}")
                sec_lines.append(f"- Why relevant: {p.get('reason')}")
                sec_lines.append("")
            return "\n".join(sec_lines)

        lines.append("### High Priority")
        lines.append("")
        lines.append(format_paper_section(high_prio))
        
        lines.append("### Medium Priority")
        lines.append("")
        lines.append(format_paper_section(med_prio))

        lines.append("### Low Priority")
        lines.append("")
        lines.append(format_paper_section(low_prio))

        return "\n".join(lines)
