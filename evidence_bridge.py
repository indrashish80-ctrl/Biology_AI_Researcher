"""
evidence_bridge.py
------------------
Bridges user experimental tabular datasets (CSV/Excel) with literature claims.
Dynamically infers factors and outcomes without hardcoded biological assumptions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from database import ResearchDB
from evidence_engine import EvidenceEngine


class EvidenceBridge:
    def __init__(self, db: ResearchDB):
        self.db = db
        self.evidence_engine = EvidenceEngine()

    def compare_experiment_to_literature(
        self,
        research_question_id: int,
        dataset_path: str,
        group_col: str,
        outcome_col: str,
        intervention_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 1. Load dataset & calculate empirical statistics deterministically
        self.evidence_engine.load_dataset(dataset_path)
        record = self.evidence_engine.build_evidence_record(group_column=group_col, outcome_column=outcome_col)
        exp_stats = record.get("computed_evidence", {}).get("experiment", {}).get("statistics", {})

        two_group = exp_stats.get("two_group_comparison")
        diff = two_group.get("mean_difference_a_minus_b", 0) if two_group else 0
        p_val = two_group.get("welch_p_value", 1.0) if two_group else 1.0
        d_val = two_group.get("cohens_d") if two_group else None

        empirical_dir = "no_effect" if p_val >= 0.05 else ("increase" if diff > 0 else "decrease")

        # 2. Dynamic factor matching: match claims matching the outcome column or intervention
        claims = self.db.claims_with_papers(research_question_id)
        comparisons = []
        replications, divergences, matches = 0, 0, 0

        target_tokens = set(outcome_col.lower().replace("_", " ").split())
        if intervention_name:
            target_tokens.update(intervention_name.lower().split())
        else:
            target_tokens.update(group_col.lower().replace("_", " ").split())

        for c in claims:
            c_text = f"{c.get('intervention', '')} {c.get('measurement', '')} {c.get('statement', '')}".lower()
            if not any(tok in c_text for tok in target_tokens if len(tok) > 2):
                continue

            matches += 1
            pub_dir = c.get("effect_direction", "unclear")
            status = "INCONCLUSIVE"

            if empirical_dir == pub_dir and empirical_dir != "unclear":
                status = "REPLICATED_PUBLISHED_EFFECT"
                replications += 1
            elif (
                empirical_dir in ("increase", "decrease")
                and pub_dir in ("increase", "decrease")
                and empirical_dir != pub_dir
            ):
                status = "DIVERGES_FROM_PUBLISHED_EFFECT"
                divergences += 1

            comparisons.append({
                "claim_id": c["id"],
                "paper": c.get("paper_title"),
                "published_direction": pub_dir,
                "empirical_direction": empirical_dir,
                "status": status,
                "empirical_p_value": p_val,
                "empirical_cohens_d": d_val,
            })

        stmt = (
            f"Experimental dataset '{dataset_path}' ({group_col} -> {outcome_col}): "
            f"observed {empirical_dir} (Welch p={p_val:.4g}, Cohen's d={d_val if d_val is not None else 0.0:.2f}). "
            f"Evaluated against {matches} literature claims: {replications} replicated, {divergences} diverged."
        )

        eid = self.db.add_evidence(
            research_question_id=research_question_id,
            evidence_type="CALCULATED",
            statement=stmt,
            source_type="experiment",
            confidence="high" if p_val < 0.05 else "medium",
            value={"comparisons": comparisons, "statistics": exp_stats, "dataset_path": dataset_path},
        )

        return {
            "evidence_id": eid,
            "statement": stmt,
            "empirical_direction": empirical_dir,
            "comparisons": comparisons,
            "replications": replications,
            "divergences": divergences,
            "matches_found": matches,
        }