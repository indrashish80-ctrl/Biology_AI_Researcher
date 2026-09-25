"""
pathway_synthesizer.py
----------------------
Cross-Study Mechanistic Pathway Synthesizer:
Connects claims across independent papers into multi-hop causal chains:
    Intervention -> Transporters/Sensors -> Signaling/TFs -> Morphology -> Biomass
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple
from database import ResearchDB


class PathwaySynthesizer:
    def __init__(self, db: ResearchDB):
        self.db = db

    def build_pathways(self, research_question_id: int) -> Dict[str, Any]:
        claims = self.db.claims_with_papers(research_question_id)
        if not claims:
            return {"chains": [], "summary": "No claims available to construct pathways."}

        # 1. Normalize nodes
        nodes: Dict[str, List[Dict[str, Any]]] = {}
        for c in claims:
            subj = str(c.get("intervention") or "").lower().strip()
            outc = str(c.get("measurement") or c.get("outcome") or "").lower().strip()
            direction = c.get("effect_direction", "unclear")
            if not subj or not outc or direction == "unclear":
                continue

            edge = {
                "claim_id": c["id"],
                "paper_id": c["paper_id"],
                "paper_title": c.get("paper_title"),
                "source": subj,
                "target": outc,
                "direction": direction,
                "quote": c.get("quote"),
                "p_value": c.get("p_value"),
            }
            nodes.setdefault(subj, []).append(edge)

        # 2. Multi-Hop Chain Discovery (e.g. A -> B and B -> C)
        chains = []
        for start_node, outgoing_edges in nodes.items():
            for edge_1 in outgoing_edges:
                intermediate = edge_1["target"]
                # Look for matching hops where intermediate is the cause
                for hop_node in nodes:
                    if hop_node in intermediate or intermediate in hop_node:
                        for edge_2 in nodes[hop_node]:
                            if edge_2["target"] != start_node:
                                chain = {
                                    "pathway": f"{start_node} -> ({edge_1['direction']}) -> {intermediate} -> ({edge_2['direction']}) -> {edge_2['target']}",
                                    "step_1": edge_1,
                                    "step_2": edge_2,
                                    "biological_interpretation": (
                                        f"Cross-study mechanism: Paper '{edge_1['paper_title'][:40]}' shows {start_node} {edge_1['direction']}s "
                                        f"{intermediate}, which Paper '{edge_2['paper_title'][:40]}' links to {edge_2['direction']} in {edge_2['target']}."
                                    ),
                                }
                                chains.append(chain)

        # 3. Deduplicate and rank chains
        seen_paths = set()
        unique_chains = []
        for ch in chains:
            if ch["pathway"] not in seen_paths:
                seen_paths.add(ch["pathway"])
                unique_chains.append(ch)

        return {
            "total_chains_discovered": len(unique_chains),
            "mechanistic_chains": unique_chains[:6],
        }