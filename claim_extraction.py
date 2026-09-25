"""
claim_extraction.py
-------------------
Extracts quote-grounded claims with per-paper quota balancing to avoid dominance.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from llm_json import LLMJSONError
from paper_extraction import DIRECTIONS, _clip, gather_parts
from stats_parsing import number_in_text, p_value_in_text, parse_p_values, quote_grounding

GROUNDING_THRESHOLD = 0.70

DIRECTION_SYNONYMS = {
    "increase": "increase", "increases": "increase", "increasing": "increase",
    "promotes": "increase", "enhances": "increase", "elevates": "increase", "higher": "increase",
    "stimulated": "increase", "activates": "increase", "upregulates": "increase",
    "decrease": "decrease", "decreases": "decrease", "decreasing": "decrease",
    "inhibits": "decrease", "reduces": "decrease", "suppresses": "decrease", "lower": "decrease",
    "downregulates": "decrease", "attenuates": "decrease",
    "no_effect": "no_effect", "no effect": "no_effect", "neutral": "no_effect", "none": "no_effect",
    "mixed": "mixed", "unclear": "unclear",
}

STAT_SENTENCE_RE = re.compile(
    r"([^.?!;\n]*\b(?:p\s*[<=><]|increased|decreased|reduced|elevated|fold|inhibited|promoted|enhanced|suppressed)[^.?!;\n]*[.?!])",
    re.IGNORECASE,
)


def derive_default_subject(question: Optional[str]) -> str:
    if not question:
        return "Experimental treatment"
    clean = re.sub(r"(?i)^(how does|what is the effect of|does|how do)\s+", "", question)
    words = clean.split()
    return " ".join(words[:3]).strip(" ?.,!").title()


def prompt_claims(chunk_type: str, text: str, question: Optional[str], stats_context: str) -> str:
    focus = f'\nFocus on findings relevant to: "{question}"\n' if question else ""
    return f"""You are extracting biological claims from a peer-reviewed biology paper.
{focus}
Extracted statistics context: {stats_context}

Extract up to 3 core biological findings.
Rules:
- "quote" must be a VERBATIM sentence fragment copied directly from the text proving the claim.
- "direction" must be one of: increase, decrease, no_effect, mixed, unclear.
- Return ONLY valid JSON:
{{
  "claims": [
    {{
      "claim": "Summary of finding",
      "subject": "Manipulated factor or drug",
      "outcome": "Measured endpoint",
      "direction": "increase",
      "p_value": 0.05 or null,
      "quote": "verbatim text copied from chunk"
    }}
  ]
}}

SECTION: {chunk_type}
TEXT:
{text}"""


def validate_claims(obj: Any) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("Need JSON object")
    for k in ("synthesis", "result", "data", "output"):
        if k in obj and isinstance(obj[k], dict):
            obj = obj[k]
            break
    raw_claims = obj.get("claims") or obj.get("findings") or []
    if not isinstance(raw_claims, list):
        raise ValueError("Expected 'claims' list")

    clean = []
    for c in raw_claims:
        if not isinstance(c, dict):
            continue
        statement = c.get("claim") or c.get("statement") or c.get("finding")
        intervention = c.get("subject") or c.get("intervention") or c.get("treatment")
        outcome = c.get("outcome") or c.get("measurement") or c.get("variable")
        quote = c.get("quote") or c.get("evidence")
        raw_dir = str(c.get("direction") or "unclear").lower().strip()
        direction = DIRECTION_SYNONYMS.get(raw_dir, "unclear")
        if not statement or not quote:
            continue
        clean.append({
            "statement": str(statement).strip(),
            "subject": str(intervention).strip() if intervention else None,
            "intervention": str(intervention).strip() if intervention else None,
            "outcome": str(outcome).strip() if outcome else None,
            "direction": direction,
            "quote": str(quote).strip().strip('"\''),
            "p_value": c.get("p_value"),
            "evidence_origin": "this_study",
        })
    return {"claims": clean}


def extract_deterministic_claims(text: str, default_subject: str = "Experimental treatment", max_claims: int = 5) -> List[Dict[str, Any]]:
    claims = []
    seen = set()
    for m in STAT_SENTENCE_RE.finditer(text):
        sentence = m.group(1).strip()
        if len(sentence) < 30 or len(sentence) > 300 or sentence in seen:
            continue
        low = sentence.lower()
        direction = "unclear"
        if any(w in low for w in ("increase", "promoted", "enhanced", "elevated", "higher", "stimulated", "activated", "upregulated")):
            direction = "increase"
        elif any(w in low for w in ("decrease", "inhibited", "reduced", "suppressed", "lower", "downregulated", "attenuated")):
            direction = "decrease"
        elif any(w in low for w in ("no significant", "not significant", "no effect", "did not affect")):
            direction = "no_effect"

        if direction == "unclear":
            continue

        outcome = "biological activity"
        if any(w in low for w in ("viability", "survival", "death", "apoptosis", "cytotoxicity")):
            outcome = "cell viability / apoptosis"
        elif any(w in low for w in ("proliferation", "growth", "biomass", "yield", "division")):
            outcome = "growth / proliferation"
        elif any(w in low for w in ("expression", "transcription", "mrna", "protein level")):
            outcome = "gene expression"

        p_vals = parse_p_values(sentence)
        p_val = p_vals[0]["value"] if p_vals else None
        quote = sentence[:220].strip()
        seen.add(sentence)

        claims.append({
            "statement": f"{default_subject} demonstrated {direction} in {outcome}.",
            "subject": default_subject,
            "intervention": default_subject,
            "outcome": outcome,
            "direction": direction,
            "quote": quote,
            "p_value": p_val,
            "evidence_origin": "this_study",
            "grounded": True,
            "grounding_score": 1.0,
            "deterministic_fallback": True,
        })
        if len(claims) >= max_claims:
            break
    return claims


def verify_claim(c: Dict[str, Any], source: str, study: Dict[str, Any]) -> Dict[str, Any]:
    flags: List[str] = []
    quote = (c.get("quote") or "").strip().strip('"\'')
    g = quote_grounding(quote, source)
    c["grounding_score"] = round(g, 2)
    c["grounded"] = g >= GROUNDING_THRESHOLD or c.get("deterministic_fallback", False)

    if not c["grounded"]:
        flags.append(f"quote not grounded in source text (score={g:.2f})")

    parsed_p = parse_p_values(quote)
    p = c.get("p_value")
    comp = None
    if p is not None:
        try:
            p = float(p)
        except (TypeError, ValueError):
            p = None

    if parsed_p:
        first = parsed_p[0]
        if p is None or abs(first["value"] - p) > 1e-12:
            p, comp = first["value"], first["comparator"]
    elif p is not None and not p_value_in_text(p, source):
        p, comp = None, None

    c["p_value"], c["p_comparator"] = p, comp
    for key, src_key in (("organism", "organism"), ("sample_size", "sample_size")):
        if not c.get(key) and study.get(src_key):
            c[key] = study[src_key]
    if not c.get("population"):
        c["population"] = study.get("tissue_or_cell_type") or c.get("organism")

    if p is not None and comp in ("<", "<=", "=") and p < 0.05 and c["direction"] == "no_effect":
        flags.append("direction 'no_effect' conflicts with p < 0.05")
        c["direction"] = "unclear"
    if p is not None and comp in ("=", ">", ">=") and p >= 0.05 and c["direction"] in ("increase", "decrease"):
        flags.append("directional claim lacks statistical significance (p >= 0.05)")
        c["nonsignificant_direction"] = True

    c["study_design"] = study.get("study_type")
    c["flags"] = flags
    return c


def get_evidence_chunks(parts: Dict[str, Any], max_paras: int = 4) -> List[Tuple[str, str]]:
    chunks = []
    if parts.get("abstract"):
        chunks.append(("Abstract", parts["abstract"]))
    body = "\n\n".join(x for x in (parts.get("results", ""), parts.get("discussion", "")) if x)
    paras = [p.strip() for p in body.split("\n\n") if len(p.strip()) > 80]
    for p in paras[:max_paras]:
        chunks.append(("Results Paragraph", p))
    return chunks


class ClaimExtractor:
    def __init__(self, db: Any, router: Any = None, providers: Optional[List[str]] = None):
        self.db = db
        self.router = router
        self.providers = providers

    def extract(
        self,
        paper_id: int,
        research_question_id: Optional[int] = None,
        question: Optional[str] = None,
        force: bool = False,
        max_claims: int = 7,
    ) -> Dict[str, Any]:
        paper = self.db.get_paper(paper_id)
        if not paper:
            raise KeyError(f"Paper {paper_id} not found")

        existing = self.db.claims_for_paper(paper_id)
        if existing and not force:
            return {"paper_id": paper_id, "skipped": True, "claims": len(existing)}

        parts = gather_parts(self.db, paper)
        if parts["basis"] == "none":
            return {"paper_id": paper_id, "status": "no_text", "claims": 0}

        source_all = "\n\n".join(
            x for x in (
                parts.get("abstract"), parts.get("results"), parts.get("results_discussion"),
                parts.get("other"), parts.get("tables"), parts.get("discussion")
            ) if x
        )
        raw = self.db.get_extraction_raw(paper_id)
        study = dict(raw.get("study") or {})
        chunks = get_evidence_chunks(parts)
        all_claims = []

        if self.router:
            prompts = [prompt_claims(c_type, _clip(c_text, 3000)[0], question, "") for c_type, c_text in chunks]
            responses = self.router.ask_parallel(prompts, max_workers=len(prompts) or 1)
            for r in responses:
                if not r:
                    continue
                try:
                    from llm_json import parse_json_response
                    parsed = validate_claims(parse_json_response(r))
                    all_claims.extend(parsed.get("claims", []))
                except Exception:
                    continue

        if not all_claims:
            subj = derive_default_subject(question)
            all_claims.extend(extract_deterministic_claims(source_all, default_subject=subj, max_claims=max_claims))

        if force:
            self.db.delete_claims_for_paper(paper_id)

        seen = set()
        saved = 0
        for c in all_claims:
            c = verify_claim(c, source_all, study)
            key = (str(c.get("intervention")).lower(), str(c.get("outcome")).lower(), c.get("direction"))
            if key in seen:
                continue
            seen.add(key)
            cid = self.db.add_claim_ext(research_question_id, paper_id, c)
            saved += 1
            if saved >= max_claims:
                break

        return {"paper_id": paper_id, "status": "ok", "claims": saved}