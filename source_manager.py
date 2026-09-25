"""
retrieval/source_manager.py
---------------------------
High-speed parallel multi-source scientific retrieval manager.
Thread-safe XML acquisition and database ingestion.
"""

from __future__ import annotations

import concurrent.futures
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from database import ResearchDB
from http_client import HttpClient
from jats_ingest import ingest_jats
from retrieval.crossref import CrossrefClient
from retrieval.europe_pmc import EuropePMCClient
from retrieval.models import PaperCandidate
from retrieval.pubmed import PubMedClient

STOP_WORDS = {
    "the", "of", "and", "in", "on", "to", "a", "an", "with", "by", "for",
    "effect", "effects", "role", "impact", "does", "how", "what", "which",
    "from", "study", "analysis", "during", "under", "using", "into"
}


def _tokenize(text: str) -> Set[str]:
    words = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
    return {w for w in words if w not in STOP_WORDS}


def sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    return re.sub(r"_+", "_", safe).strip("_")


class SourceManager:
    ALLOWED_SOURCES = ("europe_pmc", "pubmed", "pmc", "crossref")

    def __init__(
        self,
        raw_papers_dir: Optional[str | Path] = None,
        http: Optional[HttpClient] = None,
    ):
        self.raw_dir = Path(raw_papers_dir or "papers/raw")
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self.http = http or HttpClient(cache_dir="cache/retrieval")
        self.europe_pmc = EuropePMCClient(http=self.http)
        self.pubmed = PubMedClient(http=self.http)
        self.crossref = CrossrefClient(http=self.http)

    def _query_source(self, src: str, query: str, limit: int) -> List[PaperCandidate]:
        try:
            if src == "europe_pmc":
                return self.europe_pmc.search(query, max_results=limit)
            elif src == "pmc":
                return self.pubmed.search_pmc_oa(query, max_results=limit)
            elif src == "pubmed":
                return self.pubmed.search_pubmed(query, max_results=limit)
            elif src == "crossref":
                return self.crossref.search(query, max_results=limit)
        except Exception:
            pass
        return []

    def search(
        self,
        queries: List[str],
        question: Optional[str] = None,
        sources: Tuple[str, ...] = ("europe_pmc", "pmc", "pubmed", "crossref"),
        per_query_limit: int = 5,
        min_relevance: float = 0.30,
    ) -> List[PaperCandidate]:
        registry: Dict[str, PaperCandidate] = {}
        active = [s.lower().strip() for s in sources if s.lower().strip() in self.ALLOWED_SOURCES]

        tasks = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for query in queries:
                print(f"  [Retrieval] Query: '{query}'")
                for src in active:
                    tasks.append(executor.submit(self._query_source, src, query, per_query_limit))

            for future in concurrent.futures.as_completed(tasks):
                hits = future.result()
                if hits:
                    self._merge_hits(registry, hits)

        candidates = list(registry.values())
        q_tokens = _tokenize(question) if question else set()
        scored_candidates = []

        for cand in candidates:
            score = 0.0
            cand_tokens = _tokenize(f"{cand.title} {cand.abstract or ''}")
            if q_tokens:
                overlap = len(q_tokens & cand_tokens) / max(1, len(q_tokens))
                score += overlap * 0.55

            if cand.has_full_text_xml or cand.pmcid:
                score += 0.30
            elif cand.is_open_access:
                score += 0.15

            if cand.year and cand.year >= 2019:
                score += 0.10

            t_low = cand.title.lower()
            if any(w in t_low for w in ("review", "recent advances", "progress in", "perspectives on")):
                score -= 0.15
            elif any(w in t_low for w in ("effect", "response", "inhibition", "activation", "expression", "mechanism", "growth", "survival", "induction", "apoptosis", "proliferation", "pathway")):
                score += 0.10

            cand.relevance_score = score
            if score >= min_relevance:
                scored_candidates.append(cand)

        scored_candidates.sort(
            key=lambda c: (c.relevance_score, c.has_full_text_xml or bool(c.pmcid)),
            reverse=True,
        )
        return scored_candidates

    def _merge_hits(self, registry: Dict[str, PaperCandidate], hits: List[PaperCandidate]) -> None:
        for hit in hits:
            existing_key = None
            if hit.doi and f"doi:{hit.doi}" in registry:
                existing_key = f"doi:{hit.doi}"
            elif hit.pmid and f"pmid:{hit.pmid}" in registry:
                existing_key = f"pmid:{hit.pmid}"
            elif hit.pmcid and f"pmcid:{hit.pmcid}" in registry:
                existing_key = f"pmcid:{hit.pmcid}"
            elif hit.dedup_key in registry:
                existing_key = hit.dedup_key

            if existing_key:
                registry[existing_key].merge_with(hit)
            else:
                registry[hit.dedup_key] = hit

    def download_xml(self, candidate: PaperCandidate) -> Optional[Path]:
        raw_name = (
            candidate.pmcid
            or (f"pmid_{candidate.pmid}" if candidate.pmid else None)
            or (f"doi_{candidate.doi}" if candidate.doi else None)
        )
        if not raw_name:
            return None

        safe_name = sanitize_filename(raw_name)
        out_path = self.raw_dir / f"{safe_name}.xml"

        if out_path.exists() and out_path.stat().st_size > 500:
            candidate.local_xml_path = str(out_path)
            candidate.has_full_text_xml = True
            return out_path

        xml_content = None
        if candidate.pmcid:
            xml_content = self.pubmed.fetch_pmc_xml(candidate.pmcid)

        if not xml_content:
            xml_content = self.europe_pmc.fetch_full_text_xml(candidate)

        if xml_content and ("<article" in xml_content or "<pmc-articleset" in xml_content or "<?xml" in xml_content):
            out_path.write_text(xml_content, encoding="utf-8")
            candidate.local_xml_path = str(out_path)
            candidate.has_full_text_xml = True
            return out_path

        return None

    def ingest_candidate(
        self,
        db: ResearchDB,
        candidate: PaperCandidate,
        research_question_id: Optional[int] = None,
    ) -> int:
        source_query_str = "; ".join(candidate.source_queries) or candidate.source_db

        if candidate.local_xml_path and Path(candidate.local_xml_path).exists():
            pid = ingest_jats(
                db=db,
                xml_path=candidate.local_xml_path,
                research_question_id=research_question_id,
                source_query=source_query_str,
            )
            db.mark_processed("paper", candidate.dedup_key, research_question_id)
            return pid

        paper_dict = {
            "title": candidate.title,
            "authors": ", ".join(candidate.authors),
            "journal": candidate.journal,
            "year": str(candidate.year) if candidate.year else None,
            "doi": candidate.doi,
            "pmid": candidate.pmid,
            "pmcid": candidate.pmcid,
            "abstract": candidate.abstract,
            "full_text": None,
            "is_open_access": candidate.is_open_access,
        }
        pid = db.upsert_paper(research_question_id, paper_dict, source_query=source_query_str)
        db.clear_paper_sections(pid)
        db.clear_paper_tables(pid)

        if candidate.abstract:
            db.save_paper_section(pid, "abstract", "Abstract", candidate.abstract)

        db.mark_processed("paper", candidate.dedup_key, research_question_id)
        return pid

    def retrieve_and_ingest(
        self,
        db: ResearchDB,
        queries: List[str],
        question: str,
        research_question_id: int,
        max_papers: int = 10,
        min_relevance: float = 0.30,
    ) -> List[int]:
        print(f"\n[Retrieval] Discovering papers across approved scientific sources...")
        candidates = self.search(queries=queries, question=question, min_relevance=min_relevance)
        print(f"[Retrieval] Found {len(candidates)} relevant candidates.")

        # Thread-Safety Fix: Filter processed papers in the main thread first
        candidates_to_download = [
            c for c in candidates[:max_papers]
            if not db.already_processed("paper", c.dedup_key)
        ]

        # Download XML concurrently across worker threads (network only, no SQLite touch)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(self.download_xml, candidates_to_download))

        ingested_ids: List[int] = []
        for cand in candidates[:max_papers]:
            if db.already_processed("paper", cand.dedup_key):
                continue
            pid = self.ingest_candidate(db, cand, research_question_id)
            ingested_ids.append(pid)

        return ingested_ids