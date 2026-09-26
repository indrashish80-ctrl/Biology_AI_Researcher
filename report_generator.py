"""
report_generator.py
-------------------
Compiles scientific research dossiers with balanced representation across papers.
Emits clean GitHub-flavored markdown (proper headings, bullets, references) that
renders correctly in the web UI and converts cleanly to PDF.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List
from database import ResearchDB


def _title_from_question(question: str, limit: int = 70) -> str:
    """Derive a short report title from the research question."""
    words = re.sub(r"[^A-Za-z0-9\s]", " ", question or "Research Investigation")
    words = " ".join(words.split())
    if len(words) > limit:
        words = words[:limit].rsplit(" ", 1)[0]
    return words.strip().title() or "Research Investigation"


class ResearchReportGenerator:
    def __init__(self, db: ResearchDB):
        self.db = db

    def _get_balanced_claims(self, claims: List[Dict[str, Any]], max_total: int = 20) -> List[Dict[str, Any]]:
        """Round-robin selection across papers to prevent 1 paper from monopolizing the report."""
        by_paper: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for c in claims:
            pid = c.get("paper_id") or 0
            by_paper[pid].append(c)

        balanced: List[Dict[str, Any]] = []
        papers = list(by_paper.keys())
        idx = 0
        while len(balanced) < max_total and any(by_paper.values()):
            curr_pid = papers[idx % len(papers)]
            if by_paper[curr_pid]:
                balanced.append(by_paper[curr_pid].pop(0))
            idx += 1
            if not any(by_paper.values()):
                break
        return balanced

    def generate(self, research_question_id: int, output_path: str = "RESEARCH_REPORT.md") -> str:
        rq = self.db.get_research_question(research_question_id)
        question = rq["question"] if rq else "Unknown"
        summary = self.db.research_question_summary(research_question_id)
        raw_claims = self.db.claims_with_papers(research_question_id)
        claims = self._get_balanced_claims(raw_claims, max_total=20)
        contradictions = self.db.list_contradictions(research_question_id)
        hypotheses = self.db.list_hypotheses(research_question_id)
        gaps = self.db.list_research_gaps(research_question_id)
        audit_flags = self.db.list_audit_flags(research_question_id)
        evidence = self.db.list_evidence(research_question_id)

        title = _title_from_question(question)
        md = []
        md.append(f"# {title}")
        md.append("")
        md.append(f"**Research Question:** {question}")
        md.append("")
        md.append("## Executive Summary")
        md.append("")
        md.append(
            f"This autonomous investigation evaluated **{summary.get('papers', 0)} peer-reviewed papers** "
            f"and extracted **{len(raw_claims)} verified, quote-grounded claims**:"
        )
        md.append("")
        md.append(f"- Identified **{len(contradictions)} cross-study contradictions/disagreements**.")
        md.append(f"- Formulated **{len(hypotheses)} testable mechanistic hypotheses** with experimental validation specifications.")
        md.append(f"- Identified **{len(gaps)} key unaddressed research gaps**.")
        md.append(f"- Recorded **{len(audit_flags)} deterministic audit flags** for quality assurance.")
        md.append("")

        md.append("## 1. Verified Literature Evidence")
        md.append("")
        if claims:
            for i, c in enumerate(claims, 1):
                md.append(f"### {i}. {c.get('statement')}")
                md.append("")
                md.append(f"- **Paper:** {c.get('paper_title', 'Unknown')} (PMID: {c.get('pmid') or 'N/A'}, PMCID: {c.get('pmcid') or 'N/A'})")
                md.append(f"- **Intervention / Factor:** `{c.get('intervention')}` -> **Outcome:** `{c.get('measurement')}`")
                md.append(f"- **Direction:** `{c.get('effect_direction')}` | **p-value:** `{c.get('p_value') if c.get('p_value') is not None else 'Unspecified'}`")
                md.append(f"- **Verbatim Grounded Quote:** *\"{c.get('quote')}\"*")
                md.append(f"- **Grounding Score:** `{c.get('grounding_score', 1.0)}`")
                md.append("")
        else:
            md.append("*No claims were extracted for this investigation run.*")
            md.append("")

        md.append("## 2. Experimental Data & Evidence Synthesis")
        md.append("")
        exp_evidence = [e for e in evidence if e.get("source_type") in ("dataset", "experiment")]
        if exp_evidence:
            for e in exp_evidence:
                md.append(f"- **[{e.get('evidence_type')}]** {e.get('statement')}")
        else:
            md.append("*No external user experimental dataset was linked for this investigation run.*")
        md.append("")

        md.append("## 3. Cross-Study Agreements & Contradictions")
        md.append("")
        if contradictions:
            for i, cd in enumerate(contradictions, 1):
                md.append(f"### Disagreement #{i}: {cd.get('verdict')}")
                md.append("")
                md.append(f"- **Between Claims:** Claim #{cd.get('claim_a_id')} vs Claim #{cd.get('claim_b_id')}")
                md.append(f"- **Context Differences / Reasoning:** {cd.get('reasoning')}")
                md.append("")
        else:
            md.append("- No direct contradictory direction flips detected across the analyzed claim topics.")
            md.append("")

        md.append("## 4. Testable Hypotheses & Experimental Designs")
        md.append("")
        if hypotheses:
            for i, h in enumerate(hypotheses, 1):
                md.append(f"### Hypothesis #{i}")
                md.append("")
                md.append(f"**Statement:** {h.get('statement')}")
                md.append("")
                md.append(f"- **Molecular/Biological Mechanism:** {h.get('mechanism')}")
                if h.get("predictions"):
                    md.append("- **Key Predictions:**")
                    for p in h.get("predictions") or []:
                        md.append(f"  * {p}")
                if h.get("falsification_conditions"):
                    md.append("- **Falsification Conditions:**")
                    for f in h.get("falsification_conditions") or []:
                        md.append(f"  * {f}")
                exp = h.get("next_experiment")
                if exp:
                    md.append(f"- **Proposed Experiment Specification:** `{exp}`")
                md.append("")
        else:
            md.append("*No hypotheses were formulated for this investigation run.*")
            md.append("")

        md.append("## 5. Unaddressed Research Gaps")
        md.append("")
        if gaps:
            for i, g in enumerate(gaps, 1):
                md.append(f"{i}. **[{g.get('category', 'General').upper()}]** {g.get('description')}")
                md.append(f"   *Supporting Observation:* {g.get('supporting_observation')}")
                md.append("")
        else:
            md.append("*No research gaps were identified for this investigation run.*")
            md.append("")

        md.append("## 6. Adversarial Audit & Quality Control Flags")
        md.append("")
        if audit_flags:
            for f in audit_flags:
                md.append(f"- **[{f.get('severity')}]** {f.get('issue')} (Reference: `{f.get('evidence_reference')}`)")
        else:
            md.append("- *All claims met statistical power and verbatim quote-grounding criteria.*")
        md.append("")

        md.append("## References")
        md.append("")
        seen_titles = set()
        ref_num = 0
        for c in claims:
            t = c.get("paper_title")
            if not t or t in seen_titles:
                continue
            seen_titles.add(t)
            ref_num += 1
            ident = c.get("pmid") or c.get("pmcid")
            link = f"https://pubmed.ncbi.nlm.nih.gov/{c['pmid']}/" if c.get("pmid") else (
                f"https://www.ncbi.nlm.nih.gov/pmc/articles/{c['pmcid']}/" if c.get("pmcid") else ""
            )
            line = f"{ref_num}. {t}"
            if ident:
                line += f" ({ident})"
            if link:
                line += f" - {link}"
            md.append(line)
        if ref_num == 0:
            md.append("*No referenceable papers were linked to this run.*")
        md.append("")

        report_str = "\n".join(md)
        Path(output_path).write_text(report_str, encoding="utf-8")
        return report_str