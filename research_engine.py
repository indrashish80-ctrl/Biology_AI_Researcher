"""
research_engine.py
------------------
Master orchestration engine for the biology AI research stack.

Modes:
  1. Standard Scientific Investigation:
     python research_engine.py "How does metformin affect breast cancer cell proliferation and apoptosis?" --max-papers 6

  2. Closed-Loop Hypothesis Testing with Experimental CSV:
     python research_engine.py "How does metformin affect breast cancer cell proliferation and apoptosis?" \
         --data experiment.csv --group-col treatment --outcome-col viability

  3. Autonomous ReAct Agent Mode (Dynamic tool-calling loop):
     python research_engine.py "How does metformin affect breast cancer cell proliferation and apoptosis?" --agent
"""

from __future__ import annotations

import gc
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_router import AIRouter
from autonomous_agent import AutonomousResearchAgent
from bio_databases import BioDatabases, EntityLinker
from claim_extraction import ClaimExtractor
from contradiction_detection import detect_and_store, extract_conflicts_for_geo
from database import ResearchDB
from dataset_discovery import DatasetDiscovery
from evidence_bridge import EvidenceBridge
from hypothesis_evaluator import HypothesisEvaluator
from llm_json import LLMJSONError, ask_json
from paper_extraction import PaperExtractor
from pathway_synthesizer import PathwaySynthesizer
from report_generator import ResearchReportGenerator
from research_planner import generate_model_plan
from retrieval.source_manager import SourceManager
from scientific_tools import ScientificToolbox


class ResearchEngine:
    def __init__(
        self,
        db_path: Optional[str] = None,
        router: Optional[AIRouter] = None,
        raw_papers_dir: Optional[str] = "papers/raw",
        use_ai: bool = True,
    ):
        self.db = ResearchDB(db_path)
        self.router = router or (AIRouter() if use_ai else None)
        self.providers = ["groq", "nvidia", "gemini"] if self.router else None

        self.source_manager = SourceManager(raw_papers_dir=raw_papers_dir)
        self.bio_client = BioDatabases()
        self.linker = EntityLinker(self.db, bio=self.bio_client, router=self.router)
        self.dataset_discovery = DatasetDiscovery(db=self.db, router=self.router)
        self.tools = ScientificToolbox(db=self.db)
        self.bridge = EvidenceBridge(db=self.db)
        self.reporter = ResearchReportGenerator(db=self.db)
        self.pathways = PathwaySynthesizer(db=self.db)
        self.evaluator = HypothesisEvaluator(db=self.db)

    # -------------------------------------------------------------------------
    # Literature Acquisition & Processing
    # -------------------------------------------------------------------------

    def acquire_literature(
        self,
        question: str,
        research_question_id: int,
        max_papers: int = 6,
        min_relevance: float = 0.30,
    ) -> List[int]:
        queries = [question]
        if self.router:
            try:
                plan = generate_model_plan(self.router, question, provider="groq")
                if plan and plan.get("search_queries"):
                    queries = plan["search_queries"][:4]
            except Exception as exc:
                print(f"  [Planner notice] Using base question directly: {exc}")

        return self.source_manager.retrieve_and_ingest(
            db=self.db,
            queries=queries,
            question=question,
            research_question_id=research_question_id,
            max_papers=max_papers,
            min_relevance=min_relevance,
        )

    def process_papers(
        self,
        paper_ids: List[int],
        research_question_id: int,
        question: str,
        link_bio: bool = True,
        max_claims_per_paper: int = 7,
    ) -> None:
        paper_extractor = PaperExtractor(self.db, self.router, providers=self.providers)
        claim_extractor = ClaimExtractor(self.db, self.router, providers=self.providers)

        for i, pid in enumerate(paper_ids, 1):
            paper_rec = self.db.get_paper(pid)
            title = (paper_rec or {}).get("title", f"Paper #{pid}")
            print(f"\n--- [{i}/{len(paper_ids)}] Analyzing: {title[:75]} ---")

            p_res = paper_extractor.extract(pid, force=False)
            print(f"  [Design & Stats] Status: {p_res.get('status')} | Stats found: {p_res.get('n_statistics', 0)}")

            c_res = claim_extractor.extract(
                pid, research_question_id, question, force=False, max_claims=max_claims_per_paper
            )
            print(f"  [Claims] Status: {c_res.get('status')} | Verified: {c_res.get('claims', 0)}")

            if link_bio:
                try:
                    b_res = self.linker.link_paper(pid)
                    linked_count = len(b_res.get("linked", []))
                    sample = f": {', '.join(b_res.get('linked', [])[:3])}" if linked_count else ""
                    print(f"  [Entities] Linked: {linked_count} symbols (NCBI/UniProt/PubChem){sample}")
                except Exception as exc:
                    print(f"  [Entities notice] {exc}")

            del paper_rec, p_res, c_res
            gc.collect()

    # -------------------------------------------------------------------------
    # Contradictions, Pathways, and Loop Closure
    # -------------------------------------------------------------------------

    def detect_contradictions(self, research_question_id: int) -> Dict[str, Any]:
        return detect_and_store(self.db, research_question_id, router=self.router)

    def run_empirical_closure(
        self,
        research_question_id: int,
        conflicts: List[Dict[str, Any]],
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        results = []
        for c in conflicts[:limit]:
            query = f"{c['intervention']} {c['organism']}"
            print(f"\n[GEO Loop Closure] Evaluating disagreement on: '{c['intervention']}' -> '{c['outcome']}'")

            datasets = self.dataset_discovery.discover(
                question=query,
                organism=c["organism"],
                sources=("GEO",),
                per_query=4,
                min_relevance=0.20,
                research_question_id=research_question_id,
            )

            if datasets:
                top = datasets[0]
                stmt = (
                    f"Empirical series {top['accession']} identified to evaluate conflicting claims on "
                    f"'{c['intervention']}' and '{c['outcome']}' in {c['organism']}."
                )
                eid = self.db.add_evidence(
                    research_question_id=research_question_id,
                    evidence_type="OBSERVED",
                    statement=stmt,
                    source_type="dataset",
                    confidence="medium",
                    value={"geo_accession": top["accession"], "relevance_reason": top.get("relevance_reason")},
                )
                results.append({"conflict": c["group_key"], "dataset": top["accession"], "evidence_id": eid})
                print(f"  -> Linked empirical dataset: {top['accession']} ({top['title'][:65]}...)")
            else:
                print(f"  -> No public GEO series matrix found matching this conflict.")

        return results

    def synthesize_mechanistic_pathways(self, research_question_id: int) -> Dict[str, Any]:
        pathway_results = self.pathways.build_pathways(research_question_id)
        count = pathway_results.get("total_chains_discovered", 0)
        print(f"  -> Discovered {count} cross-study mechanistic pathway chains.")
        for ch in pathway_results.get("mechanistic_chains", [])[:3]:
            print(f"     * {ch['pathway']}")
        return pathway_results

    # -------------------------------------------------------------------------
    # Hypotheses & Research Gaps (Dynamic Universal Synthesis)
    # -------------------------------------------------------------------------

    def formulate_hypotheses_and_gaps(
        self,
        research_question_id: int,
        question: str,
    ) -> Dict[str, Any]:
        claims = self.db.claims_with_papers(research_question_id)
        contradictions = self.db.list_contradictions(research_question_id)

        evidence_summary = [
            f"- Paper: {c.get('paper_title', 'Unknown')} | {c.get('intervention')} -> {c.get('effect_direction')} "
            f"in {c.get('measurement')} (p={c.get('p_value')}, n={c.get('sample_size')})"
            for c in claims[:15]
        ]
        conflict_summary = [
            f"- Conflict between claim {c['claim_a_id']} and {c['claim_b_id']}: verdict={c['verdict']} ({c.get('reasoning')})"
            for c in contradictions[:5]
        ]

        prompt = f"""You are a senior scientific synthesis engine in a biology research pipeline.

Research Question: {question}

Observed Evidence:
{chr(10).join(evidence_summary) if evidence_summary else 'No specific claim statistics recorded.'}

Detected Cross-Study Disagreements:
{chr(10).join(conflict_summary) if conflict_summary else 'No severe contradictions detected; findings cover complementary biological axes.'}

Generate:
1. Exactly 2 mechanistic, falsifiable hypotheses that explain the observed biological findings or reconcile disagreements.
2. For each hypothesis, design a concrete next-step validation experiment with clear controls and a falsification condition.
3. Exactly 2 critical research gaps that remain unaddressed by the current literature.

Return ONLY valid JSON matching this schema:
{{
  "hypotheses": [
    {{
      "statement": "Clear testable statement",
      "mechanism": "Proposed molecular/physiological pathway",
      "predictions": ["prediction 1", "prediction 2"],
      "falsification_conditions": ["condition that would refute this"],
      "next_experiment": {{
        "experiment_title": "...",
        "controls": "...",
        "independent_variable": "...",
        "dependent_variable": "...",
        "power_notes": "sample size and replication requirements"
      }}
    }}
  ],
  "research_gaps": [
    {{
      "description": "...",
      "category": "dosage|timing|mechanism|organism_generalization",
      "supporting_observation": "..."
    }}
  ]
}}"""

        def validate(obj: Any) -> Dict[str, Any]:
            if not isinstance(obj, dict):
                raise ValueError("Response must be a JSON object.")

            for wrap_key in ("synthesis", "result", "data", "output", "response", "analysis"):
                if wrap_key in obj and isinstance(obj[wrap_key], dict):
                    obj = obj[wrap_key]
                    break

            raw_hypotheses = obj.get("hypotheses") or obj.get("hypothesis") or []
            raw_gaps = obj.get("research_gaps") or obj.get("gaps") or []

            if isinstance(raw_hypotheses, dict):
                raw_hypotheses = [raw_hypotheses]
            if isinstance(raw_gaps, dict):
                raw_gaps = [raw_gaps]

            if not isinstance(raw_hypotheses, list) or not isinstance(raw_gaps, list):
                raise ValueError("Expected lists for hypotheses and research_gaps.")

            clean_hypotheses = []
            for h in raw_hypotheses:
                if not isinstance(h, dict):
                    continue
                preds = h.get("predictions")
                if isinstance(preds, str):
                    preds = [preds]
                elif not isinstance(preds, list):
                    preds = ["Measurable biological response"]

                falsif = h.get("falsification_conditions")
                if isinstance(falsif, str):
                    falsif = [falsif]
                elif not isinstance(falsif, list):
                    falsif = ["No statistically significant effect detected upon replication"]

                next_exp = h.get("next_experiment")
                if not isinstance(next_exp, dict):
                    next_exp = {"experiment_title": str(next_exp or "Replication assay")}

                clean_hypotheses.append({
                    "statement": str(h.get("statement") or "Proposed biological hypothesis"),
                    "mechanism": str(h.get("mechanism") or "Regulatory molecular pathway"),
                    "predictions": preds,
                    "falsification_conditions": falsif,
                    "next_experiment": next_exp,
                })

            clean_gaps = []
            for g in raw_gaps:
                if isinstance(g, str):
                    clean_gaps.append({
                        "description": g.strip(),
                        "category": "generalization",
                        "supporting_observation": "Identified from cross-study literature gaps",
                    })
                elif isinstance(g, dict):
                    clean_gaps.append({
                        "description": str(g.get("description") or "Unaddressed research gap"),
                        "category": str(g.get("category") or "mechanism"),
                        "supporting_observation": str(g.get("supporting_observation") or "Literature boundary"),
                    })

            if not clean_hypotheses and not clean_gaps:
                raise ValueError("No valid hypotheses or research gaps parsed.")

            return {"hypotheses": clean_hypotheses, "research_gaps": clean_gaps}

        res = None
        if self.router:
            try:
                res = ask_json(self.router, prompt, validate=validate, providers=self.providers)
            except Exception as exc:
                print(f"  [AI synthesis notice] Falling back to dynamic hypothesis generator: {exc}")

        if not res or not res.get("hypotheses"):
            res = self._deterministic_hypothesis_fallback(question, claims, contradictions)

        created_hypotheses = []
        for h in res.get("hypotheses", []):
            hid = self.db.add_hypothesis(
                research_question_id=research_question_id,
                hypothesis={
                    "statement": h.get("statement", ""),
                    "mechanism": h.get("mechanism"),
                    "predictions": h.get("predictions", []),
                    "falsification_conditions": h.get("falsification_conditions", []),
                    "supporting_evidence": evidence_summary[:3],
                    "next_experiment": json.dumps(h.get("next_experiment", {})),
                    "status": "proposed",
                },
            )
            if h.get("next_experiment"):
                self.db.add_experiment_design(
                    hypothesis_id=hid,
                    design=h["next_experiment"],
                    power_notes=h["next_experiment"].get("power_notes", "Sample size >= 12 across 3 independent replicates"),
                    confounder_notes="Randomized placement with untreated vehicle controls.",
                )
            created_hypotheses.append({"id": hid, **h})

        created_gaps = []
        for g in res.get("research_gaps", []):
            gid = self.db.add_research_gap(
                research_question_id=research_question_id,
                description=g.get("description", ""),
                category=g.get("category", "general"),
                supporting_observation=g.get("supporting_observation", ""),
            )
            created_gaps.append({"id": gid, **g})

        return {"hypotheses": created_hypotheses, "research_gaps": created_gaps}

    def _deterministic_hypothesis_fallback(
        self,
        question: str,
        claims: list,
        contradictions: list,
    ) -> Dict[str, Any]:
        """Dynamically derives universal hypotheses from actual question tokens and claims."""
        clean_q = re.sub(r"(?i)^(how does|what is the effect of|does|how do)\s+", "", question).strip(" ?.")
        factor = clean_q.split(" affect ")[0] if " affect " in clean_q else clean_q.split()[0]
        endpoint = clean_q.split(" affect ")[-1] if " affect " in clean_q else "biological response"

        if claims:
            c0 = claims[0]
            if c0.get("intervention"):
                factor = c0["intervention"]
            if c0.get("measurement"):
                endpoint = c0["measurement"]

        return {
            "hypotheses": [
                {
                    "statement": f"{factor.capitalize()} regulates {endpoint} via concentration-dependent signaling threshold.",
                    "mechanism": f"Basal engagement of {factor} mediates homeostasis, whereas supra-threshold exposure activates adaptive regulatory loops.",
                    "predictions": [
                        f"{endpoint.capitalize()} shows a saturable dose-response curve under escalating doses of {factor}.",
                        f"Inhibition of downstream effectors blunts {factor}-mediated modulation of {endpoint}."
                    ],
                    "falsification_conditions": [
                        f"No statistically significant difference in {endpoint} is observed across treatment gradients (p >= 0.05)."
                    ],
                    "next_experiment": {
                        "experiment_title": f"Dose-Response Gradient Assay for {factor}",
                        "controls": "Untreated baseline and vehicle-only control",
                        "independent_variable": f"Graded concentrations of {factor}",
                        "dependent_variable": endpoint,
                        "power_notes": "Minimum n = 12 biological replicates across 3 independent blocks"
                    }
                }
            ],
            "research_gaps": [
                {
                    "description": f"Lack of longitudinal kinetics evaluating acute vs chronic effects of {factor} on {endpoint}.",
                    "category": "timing",
                    "supporting_observation": "Literature predominantly captures single static timepoints."
                },
                {
                    "description": f"Unclear translation of {factor} effects across divergent genetic backgrounds or microenvironments.",
                    "category": "generalization",
                    "supporting_observation": "Observed variation in effect sizes across independent experimental models."
                }
            ]
        }

    # -------------------------------------------------------------------------
    # Quality Auditing & Empirical Evaluation
    # -------------------------------------------------------------------------

    def audit_findings(self, research_question_id: int) -> List[Dict[str, Any]]:
        claims = self.db.claims_with_papers(research_question_id)
        flags = []

        for c in claims:
            if c.get("effect_direction") == "no_effect" and c.get("sample_size") and c["sample_size"] < 10:
                fid = self.db.add_audit_flag(
                    research_question_id=research_question_id,
                    entity_type="claim",
                    entity_id=c["id"],
                    claim_text=c.get("statement", ""),
                    evidence_reference=f"paper:{c.get('paper_id')}",
                    issue=f"Reported 'no_effect' with small sample size (n={c['sample_size']}). Risk of Type II error.",
                    severity="MEDIUM",
                )
                flags.append({"flag_id": fid, "claim_id": c["id"], "severity": "MEDIUM", "issue": "underpowered_null"})

            if c.get("nonsignificant_direction"):
                fid = self.db.add_audit_flag(
                    research_question_id=research_question_id,
                    entity_type="claim",
                    entity_id=c["id"],
                    claim_text=c.get("statement", ""),
                    evidence_reference=f"paper:{c.get('paper_id')}",
                    issue="Directional biological claim reported without p < 0.05 statistical significance.",
                    severity="HIGH",
                )
                flags.append({"flag_id": fid, "claim_id": c["id"], "severity": "HIGH", "issue": "nonsignificant_trend"})

            if not c.get("grounded"):
                fid = self.db.add_audit_flag(
                    research_question_id=research_question_id,
                    entity_type="claim",
                    entity_id=c["id"],
                    claim_text=c.get("statement", ""),
                    evidence_reference=f"paper:{c.get('paper_id')}",
                    issue="Quote could not be grounded in source text (grounding < 0.70). Demoted to AI inference.",
                    severity="HIGH",
                )
                flags.append({"flag_id": fid, "claim_id": c["id"], "severity": "HIGH", "issue": "ungrounded_quote"})

        return flags

    def evaluate_hypothesis_with_data(
        self,
        research_question_id: int,
        dataset_path: str,
        group_column: str,
        outcome_column: str,
    ) -> Optional[Dict[str, Any]]:
        hypotheses = self.db.list_hypotheses(research_question_id)
        if not hypotheses:
            return None

        target_h = hypotheses[0]
        eval_res = self.evaluator.evaluate_hypothesis_with_data(
            hypothesis_id=target_h["id"],
            dataset_path=dataset_path,
            group_column=group_column,
            outcome_column=outcome_column,
        )
        print(f"\n[Empirical Falsification Loop] Hypothesis #{target_h['id']} -> Status: {eval_res['new_status'].upper()}")
        print(f"  -> {eval_res['verdict']}")
        return eval_res

    # -------------------------------------------------------------------------
    # Autonomous ReAct Agent Entrypoint
    # -------------------------------------------------------------------------

    def run_agent(self, question: str, max_steps: int = 20) -> Dict[str, Any]:
        """Run an autonomous, dynamic tool-calling ReAct agent scoped to the question's queue."""
        if not self.router:
            raise RuntimeError("Autonomous agent requires an active AI router.")
        rq_id = self.db.create_research_question(question)
        agent = AutonomousResearchAgent(
            db=self.db,
            router=self.router,
            max_steps=max_steps,
            research_question_id=rq_id,
        )
        return agent.run(question)

    # -------------------------------------------------------------------------
    # Batch Pipeline Investigation Entrypoint
    # -------------------------------------------------------------------------

    def investigate(
        self,
        question: str,
        experimental_dataset: Optional[str] = None,
        exp_group_col: Optional[str] = None,
        exp_outcome_col: Optional[str] = None,
        max_papers: int = 6,
        min_relevance: float = 0.30,
        enable_geo: bool = True,
        output_report: str = "RESEARCH_REPORT.md",
    ) -> Dict[str, Any]:
        print("=" * 80)
        print("BIOLOGY AI RESEARCH ENGINE - CLOSED-LOOP INVESTIGATION")
        print(f"Question: {question}")
        print("=" * 80)

        rq_id = self.db.create_research_question(question)

        paper_ids = self.acquire_literature(
            question=question,
            research_question_id=rq_id,
            max_papers=max_papers,
            min_relevance=min_relevance,
        )

        if not paper_ids:
            paper_ids = [p["id"] for p in self.db.list_papers(rq_id)]

        print(f"\nProcessing {len(paper_ids)} papers in active knowledge base...")
        self.process_papers(paper_ids, rq_id, question)

        if experimental_dataset and exp_group_col and exp_outcome_col:
            print("\n" + "=" * 80)
            print("CONNECTING USER EXPERIMENTAL DATA TO LITERATURE")
            print("=" * 80)
            bridge_res = self.bridge.compare_experiment_to_literature(
                research_question_id=rq_id,
                dataset_path=experimental_dataset,
                group_col=exp_group_col,
                outcome_col=exp_outcome_col,
            )
            print(f"  -> {bridge_res['statement']}")

        print("\n" + "=" * 80)
        print("SYNTHESIZING CROSS-STUDY CONTRADICTIONS")
        print("=" * 80)
        contradictions = self.detect_contradictions(rq_id)

        all_claims = self.db.claims_with_papers(rq_id)
        conflict_targets = extract_conflicts_for_geo(contradictions, all_claims)

        geo_results = []
        if enable_geo and conflict_targets:
            geo_results = self.run_empirical_closure(rq_id, conflict_targets)

        print("\n" + "=" * 80)
        print("CONSTRUCTING MULTI-HOP MECHANISTIC PATHWAYS")
        print("=" * 80)
        pathway_results = self.synthesize_mechanistic_pathways(rq_id)

        print("\n" + "=" * 80)
        print("FORMULATING HYPOTHESES & EXPERIMENTAL DESIGNS")
        print("=" * 80)
        synthesis = self.formulate_hypotheses_and_gaps(rq_id, question)
        print(f"  -> Generated {len(synthesis['hypotheses'])} falsifiable hypotheses.")
        print(f"  -> Identified {len(synthesis['research_gaps'])} unaddressed research gaps.")

        falsification_res = None
        if experimental_dataset and exp_group_col and exp_outcome_col:
            falsification_res = self.evaluate_hypothesis_with_data(
                research_question_id=rq_id,
                dataset_path=experimental_dataset,
                group_column=exp_group_col,
                outcome_column=exp_outcome_col,
            )

        audit_flags = self.audit_findings(rq_id)
        print(f"  -> Logged {len(audit_flags)} deterministic audit flags.")

        self.reporter.generate(rq_id, output_path=output_report)
        print("\n" + "=" * 80)
        print(f"INVESTIGATION COMPLETE: Report saved to {output_report}")
        print("=" * 80)

        summary = self.db.research_question_summary(rq_id)
        dossier = {
            "research_question_id": rq_id,
            "research_question": question,
            "papers_analyzed": len(paper_ids),
            "evidence_summary": summary,
            "contradiction_summary": {
                "claim_groups_analyzed": len(contradictions.get("groups", [])),
                "conflicting_groups_found": contradictions.get("n_conflict_groups", 0),
                "conflicting_pairs": contradictions.get("n_conflicting_pairs", 0),
            },
            "pathway_chains": pathway_results.get("mechanistic_chains", []),
            "empirical_geo_closures": geo_results,
            "hypotheses": synthesis["hypotheses"],
            "research_gaps": synthesis["research_gaps"],
            "falsification_evaluation": falsification_res,
            "audit_flags": audit_flags,
            "report_path": output_report,
            "status": "investigation_complete",
        }

        out_path = Path(f"research_dossier_{rq_id}.json")
        out_path.write_text(json.dumps(dossier, indent=2, ensure_ascii=False), encoding="utf-8")
        return dossier

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# -----------------------------------------------------------------------------
# Command Line Interface (CLI) Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Biology AI Research Engine CLI.")
    parser.add_argument("question", help="Biological research question to investigate")
    parser.add_argument("--max-papers", type=int, default=6, help="Max papers to retrieve and analyze")
    parser.add_argument("--min-relevance", type=float, default=0.30, help="Relevance cutoff (0.0 to 1.0)")
    parser.add_argument("--data", default=None, help="Optional user experimental dataset CSV/Excel")
    parser.add_argument("--group-col", default=None, help="Grouping/treatment column in user dataset")
    parser.add_argument("--outcome-col", default=None, help="Measured outcome column in user dataset")
    parser.add_argument("--output", default="RESEARCH_REPORT.md", help="Output Markdown report path")
    parser.add_argument("--agent", action="store_true", help="Run in autonomous ReAct tool-calling agent mode")
    parser.add_argument("--steps", type=int, default=20, help="Max step budget for agent mode")
    parser.add_argument("--no-geo", action="store_true", help="Skip automated GEO loop closure")
    args = parser.parse_args()

    with ResearchEngine() as engine:
        if args.agent:
            engine.run_agent(args.question, max_steps=args.steps)
        else:
            engine.investigate(
                question=args.question,
                experimental_dataset=args.data,
                exp_group_col=args.group_col,
                exp_outcome_col=args.outcome_col,
                max_papers=args.max_papers,
                min_relevance=args.min_relevance,
                enable_geo=not args.no_geo,
                output_report=args.output,
            )