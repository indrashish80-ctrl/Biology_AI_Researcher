"""
contradiction_detection.py
--------------------------
Universal biological contradiction detection and contextual difference adjudicator.
Uses biological axis mapping to reliably detect cross-study conflicts.
"""

from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

DIRECTIONAL = ("increase", "decrease", "no_effect")

# Biological Axes definition
AXIS_MAPPINGS = {
    "cell_survival": {
        "viability", "survival", "growth", "proliferation", "biomass",
        "yield", "colony", "division", "weight", "dry_weight"
    },
    "cell_death": {
        "apoptosis", "necrosis", "cytotoxicity", "death", "cell_death",
        "lethal", "caspase", "tunel", "ldh"
    },
    "expression": {
        "expression", "transcription", "mrna", "abundance", "accumulation", "level"
    },
    "signaling": {
        "phosphorylation", "activation", "induction", "kinase", "signaling"
    },
    "inhibition": {
        "inhibition", "suppression", "downregulation", "decrease", "attenuation", "blockade"
    }
}

OPPOSING_AXES = {
    ("cell_survival", "cell_death"),
    ("cell_death", "cell_survival"),
}

STOP_WORDS = {
    "the", "of", "and", "in", "on", "to", "a", "an", "with", "by", "for", "effect",
    "effects", "treatment", "treated", "application", "applied", "concentration", "exposure",
    "response", "responses", "during", "after", "via", "through", "associated", "cell", "cells"
}


def tokens(s: Optional[str]) -> Set[str]:
    if not s:
        return set()
    words = re.findall(r"[a-zA-Z0-9\-]+", s.lower())
    return {w for w in words if w not in STOP_WORDS and len(w) > 2}


def map_to_axis(term: Optional[str]) -> str:
    if not term:
        return "unclassified"
    toks = tokens(term)
    for axis, keywords in AXIS_MAPPINGS.items():
        if toks & keywords or any(kw in term.lower() for kw in keywords):
            return axis
    return "unclassified"


def containment(a: Set[str], b: Set[str]) -> float:
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def same_topic(a: Dict[str, Any], b: Dict[str, Any], threshold: float = 0.40) -> bool:
    tok_ia = tokens(a.get("intervention") or a.get("subject"))
    tok_ib = tokens(b.get("intervention") or b.get("subject"))
    interv_sim = containment(tok_ia, tok_ib) if (tok_ia and tok_ib) else 0.0

    axis_a = map_to_axis(a.get("outcome") or a.get("measurement"))
    axis_b = map_to_axis(b.get("outcome") or b.get("measurement"))

    same_axis = (axis_a == axis_b and axis_a != "unclassified")
    opposing_axis = (axis_a, axis_b) in OPPOSING_AXES

    tok_oa = tokens(a.get("outcome") or a.get("measurement"))
    tok_ob = tokens(b.get("outcome") or b.get("measurement"))
    outc_sim = containment(tok_oa, tok_ob) if (tok_oa and tok_ob) else 0.0

    return (interv_sim >= threshold) and (same_axis or opposing_axis or outc_sim >= threshold)


def effective_direction(c: Dict[str, Any]) -> str:
    d = c.get("effect_direction") or c.get("direction") or "unclear"
    if c.get("nonsignificant_direction"):
        return "unclear"
    return d


def group_claims(claims: List[Dict[str, Any]], threshold: float = 0.40) -> List[List[Dict[str, Any]]]:
    parent = list(range(len(claims)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in combinations(range(len(claims)), 2):
        if same_topic(claims[i], claims[j], threshold):
            parent[find(i)] = find(j)

    buckets: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for i, c in enumerate(claims):
        buckets[find(i)].append(c)
    return sorted(buckets.values(), key=lambda g: -len(g))


def compare_claims(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    diffs = []
    unknown = []

    oa = str(a.get("organism") or "").lower().strip()
    ob = str(b.get("organism") or "").lower().strip()
    if oa and ob and oa != ob and oa not in ob and ob not in oa:
        diffs.append({"factor": "organism", "a": oa, "b": ob})
    elif not (oa and ob):
        unknown.append("organism")

    na, nb = a.get("sample_size"), b.get("sample_size")
    if na and nb and max(na, nb) / max(1, min(na, nb)) >= 3:
        diffs.append({"factor": "sample_size_power", "a": na, "b": nb})

    # Check for axis inversion
    axis_a = map_to_axis(a.get("outcome") or a.get("measurement"))
    axis_b = map_to_axis(b.get("outcome") or b.get("measurement"))
    if (axis_a, axis_b) in OPPOSING_AXES:
        diffs.append({"factor": "opposing_endpoint_axes", "a": axis_a, "b": axis_b})

    material_diffs = [d for d in diffs if d["factor"] not in ("sample_size_power", "opposing_endpoint_axes")]
    if material_diffs:
        verdict = "CONTEXT_DIFFERENCE"
    elif len(unknown) >= 2:
        verdict = "UNCLEAR"
    else:
        verdict = "TRUE_CONTRADICTION"

    return {"verdict": verdict, "differences": diffs, "unknown_fields": unknown}


def detect_and_store(db: Any, research_question_id: Optional[int], router: Any = None, **kwargs) -> Dict[str, Any]:
    claims = db.claims_with_papers(research_question_id)
    groups = group_claims(claims)
    db.clear_contradictions(research_question_id)

    n_pairs = 0
    conflict_groups = 0
    out_groups = []

    for members in groups:
        by_dir = defaultdict(list)
        for m in members:
            by_dir[effective_direction(m)].append(m["id"])

        pairs = []
        for a, b in combinations(members, 2):
            da, dbb = effective_direction(a), effective_direction(b)
            axis_a = map_to_axis(a.get("outcome") or a.get("measurement"))
            axis_b = map_to_axis(b.get("outcome") or b.get("measurement"))

            is_direct_flip = (da in DIRECTIONAL and dbb in DIRECTIONAL and da != dbb and axis_a == axis_b)
            is_axis_conflict = ((axis_a, axis_b) in OPPOSING_AXES and da == dbb and da in ("increase", "decrease"))

            if is_direct_flip or is_axis_conflict:
                cmpd = compare_claims(a, b)
                reasoning = "; ".join(f"{d['factor']}: {d['a']} vs {d['b']}" for d in cmpd["differences"]) or "Directional contrast"
                db.add_contradiction(research_question_id, a["id"], b["id"], cmpd["verdict"], cmpd, reasoning)
                pairs.append({"claim_a": a["id"], "claim_b": b["id"], "verdict": cmpd["verdict"], "reasoning": reasoning})
                n_pairs += 1

        has_conflict = len(pairs) > 0
        if has_conflict:
            conflict_groups += 1

        interv = members[0].get("intervention") or members[0].get("subject") or "Biological Factor"
        outc = members[0].get("measurement") or members[0].get("outcome") or "Endpoint"
        key = f"{interv}::{outc}"
        summary = {"n_claims": len(members), "directions": dict(by_dir), "has_conflict": has_conflict}

        db.save_claim_group(research_question_id, key, interv, outc, [m["id"] for m in members], summary, [])
        out_groups.append({"key": key, "intervention": interv, "outcome": outc, "summary": summary, "pairs": pairs})

    return {"groups": out_groups, "n_conflict_groups": conflict_groups, "n_conflicting_pairs": n_pairs}


def extract_conflicts_for_geo(analysis_result: Dict[str, Any], claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    claims_by_id = {c["id"]: c for c in claims}
    targets = []
    for g in analysis_result.get("groups", []):
        if not g.get("summary", {}).get("has_conflict"):
            continue
        members = [claims_by_id[cid] for cid in g.get("summary", {}).get("member_ids", []) if cid in claims_by_id]
        organisms = {m.get("organism") for m in members if m.get("organism")}
        org = organisms.pop() if organisms else None
        targets.append({
            "group_key": g["key"],
            "intervention": g["intervention"],
            "outcome": g["outcome"],
            "organism": org,
            "conflicting_directions": list(g["summary"]["directions"].keys()),
        })
    return targets