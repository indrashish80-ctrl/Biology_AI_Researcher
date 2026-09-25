"""
report_generator.py
-------------------
Compiles scientific research dossiers with balanced representation across papers.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List
from database import ResearchDB


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

        md = []
        md.append("================================================================================")
        md.append("                         AUTONOMOUS SCIENTIFIC RESEARCH REPORT                  ")
        md.append("================================================================================\n")
        md.append(f"**Research Question:** {question}\n")
        md.append("## Executive Summary\n")
        md.append(
            f"This autonomous investigation evaluated **{summary.get('papers', 0)} peer-reviewed papers** "
            f"and extracted **{len(raw_claims)} verified, quote-grounded claims**.\n"
            f"- Identified **{len(contradictions)} cross-study contradictions/disagreements**.\n"
            f"- Formulated **{len(hypotheses)} testable mechanistic hypotheses** with experimental validation specifications.\n"
            f"- Identified **{len(gaps)} key unaddressed research gaps**.\n"
            f"- Recorded **{len(audit_flags)} deterministic audit flags** for quality assurance.\n"
        )

        md.append("## 1. Verified Literature Evidence (Balanced Cross-Study View)\n")
        for i, c in enumerate(claims, 1):
            md.append(f"### [{i}] {c.get('statement')}")
            md.append(f"- **Paper:** {c.get('paper_title', 'Unknown')} (PMID: {c.get('pmid') or 'N/A'}, PMCID: {c.get('pmcid') or 'N/A'})")
            md.append(f"- **Intervention / Factor:** `{c.get('intervention')}` -> **Outcome:** `{c.get('measurement')}`")
            md.append(f"- **Direction:** `{c.get('effect_direction')}` | **p-value:** `{c.get('p_value') if c.get('p_value') is not None else 'Unspecified'}`")
            md.append(f"- **Verbatim Grounded Quote:** *\"{c.get('quote')}\"*")
            md.append(f"- **Grounding Score:** `{c.get('grounding_score', 1.0)}`\n")

        md.append("## 2. Experimental Data & Evidence Synthesis\n")
        exp_evidence = [e for e in evidence if e.get("source_type") in ("dataset", "experiment")]
        if exp_evidence:
            for e in exp_evidence:
                md.append(f"- **[{e.get('evidence_type')}]:** {e.get('statement')}")
        else:
            md.append("*No external user experimental dataset was linked for this investigation run.*")
        md.append("")

        md.append("## 3. Cross-Study Agreements & Contradictions\n")
        if contradictions:
            for i, cd in enumerate(contradictions, 1):
                md.append(f"### Disagreement #{i}: {cd.get('verdict')}")
                md.append(f"- **Between Claims:** Claim #{cd.get('claim_a_id')} vs Claim #{cd.get('claim_b_id')}")
                md.append(f"- **Context Differences / Reasoning:** {cd.get('reasoning')}\n")
        else:
            md.append("- No direct contradictory direction flips detected across the analyzed claim topics.\n")

        md.append("## 4. Testable Hypotheses & Experimental Designs\n")
        for i, h in enumerate(hypotheses, 1):
            md.append(f"### Hypothesis #{i}: {h.get('statement')}")
            md.append(f"- **Molecular/Biological Mechanism:** {h.get('mechanism')}")
            md.append(f"- **Key Predictions:**")
            for p in h.get("predictions") or []:
                md.append(f"  * {p}")
            md.append(f"- **Falsification Conditions:**")
            for f in h.get("falsification_conditions") or []:
                md.append(f"  * {f}")
            exp = h.get("next_experiment")
            if exp:
                md.append(f"- **Proposed Experiment Specification:** `{exp}`\n")

        md.append("## 5. Unaddressed Research Gaps\n")
        for i, g in enumerate(gaps, 1):
            md.append(f"{i}. **[{g.get('category', 'General').upper()}]** {g.get('description')}")
            md.append(f"   *Supporting Observation:* {g.get('supporting_observation')}\n")

        md.append("## 6. Adversarial Audit & Quality Control Flags\n")
        if audit_flags:
            for f in audit_flags:
                md.append(f"- **[{f.get('severity')}]** {f.get('issue')} (Reference: `{f.get('evidence_reference')}`)")
        else:
            md.append("- *All claims met statistical power and verbatim quote-grounding criteria.*")

        report_str = "\n".join(md)
        Path(output_path).write_text(report_str, encoding="utf-8")
        return report_str