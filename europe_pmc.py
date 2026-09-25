"""
retrieval/europe_pmc.py
-----------------------
Europe PMC client with resilient query formatting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from http_client import HttpClient, HttpError
from retrieval.models import PaperCandidate, clean_pmcid, clean_text

EUROPE_PMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


class EuropePMCClient:
    def __init__(self, http: Optional[HttpClient] = None):
        self.http = http or HttpClient(cache_dir="cache/retrieval/europe_pmc")

    def search(
        self,
        query: str,
        max_results: int = 10,
        open_access_only: bool = False,
    ) -> List[PaperCandidate]:
        """Search Europe PMC without query expansion that causes 503 timeouts."""
        q = query
        if open_access_only:
            q = f"({query}) AND OPEN_ACCESS:Y"

        params = {
            "query": q,
            "format": "json",
            "resultType": "core",
            "pageSize": str(max_results),
            "synonym": "false",  # prevents Solr backend timeouts
        }

        try:
            data = self.http.get_json(f"{EUROPE_PMC_BASE}/search", params=params)
        except HttpError as exc:
            print(f"  [EuropePMC] API temporarily unavailable: {exc}")
            return []

        results = (data.get("resultList") or {}).get("result") or []
        candidates: List[PaperCandidate] = []

        for item in results:
            if not isinstance(item, dict):
                continue

            title = clean_text(item.get("title"))
            if not title:
                continue

            authors_str = item.get("authorString") or ""
            authors = [clean_text(a) for a in authors_str.split(",") if a.strip()]

            year = None
            if item.get("pubYear"):
                try:
                    year = int(item["pubYear"])
                except ValueError:
                    pass

            is_oa = item.get("isOpenAccess") == "Y"
            raw_pmcid = clean_pmcid(item.get("pmcid"))
            has_xml = (
                item.get("hasXML") == "Y"
                or item.get("hasBookXML") == "Y"
                or bool(raw_pmcid)
            )

            cand = PaperCandidate(
                title=title,
                authors=authors,
                journal=clean_text(item.get("journalTitle")),
                year=year,
                doi=item.get("doi"),
                pmid=item.get("pmid"),
                pmcid=raw_pmcid,
                abstract=clean_text(item.get("abstractText")),
                is_open_access=is_oa,
                source_db="europe_pmc",
                source_queries=[f"europe_pmc:{query}"],
                url=f"https://europepmc.org/article/{item.get('source', 'MED')}/{item.get('id', '')}",
                has_full_text_xml=has_xml,
                raw_metadata={
                    "source": item.get("source"),
                    "id": item.get("id"),
                    "citedByCount": item.get("citedByCount"),
                },
            )
            candidates.append(cand)

        return candidates

    def fetch_full_text_xml(self, candidate: PaperCandidate) -> Optional[str]:
        raw_meta = candidate.raw_metadata or {}
        src = raw_meta.get("source") or ("PMC" if candidate.pmcid else "MED")
        rec_id = candidate.pmcid or candidate.pmid or raw_meta.get("id")

        if not rec_id:
            return None

        url = f"{EUROPE_PMC_BASE}/{src}/{rec_id}/fullTextXML"

        try:
            xml_text = self.http.get_text(url)
            if "<article" in xml_text or "<?xml" in xml_text or "<pmc-articleset" in xml_text:
                return xml_text
        except HttpError:
            pass

        if candidate.pmcid and rec_id != candidate.pmcid:
            try:
                alt_url = f"{EUROPE_PMC_BASE}/PMC/{candidate.pmcid}/fullTextXML"
                xml_text = self.http.get_text(alt_url)
                if "<article" in xml_text or "<?xml" in xml_text:
                    return xml_text
            except HttpError:
                pass

        return None