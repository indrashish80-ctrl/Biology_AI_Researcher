"""
retrieval/pubmed.py
-------------------
NCBI E-Utilities client for PubMed and PMC open access with rate compliance.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional

from http_client import HttpClient, HttpError
from retrieval.models import PaperCandidate, clean_pmcid, clean_text

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedClient:
    def __init__(self, http: Optional[HttpClient] = None):
        self.http = http or HttpClient(cache_dir="cache/retrieval/ncbi")
        self.api_key = os.getenv("NCBI_API_KEY")

    def _params(self, base_params: Dict[str, Any]) -> Dict[str, Any]:
        p = dict(base_params)
        p.setdefault("retmode", "json")
        p.setdefault("tool", "BiologyAIResearcher")
        p.setdefault("email", "researcher@biopipeline.org")
        if self.api_key:
            p["api_key"] = self.api_key
        return p

    def search_pubmed(self, query: str, max_results: int = 10) -> List[PaperCandidate]:
        """Search PubMed and parse metadata safely."""
        time.sleep(0.35)  # Respect NCBI 3 req/sec limit
        search_params = self._params({
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "sort": "relevance",
        })

        try:
            res = self.http.get_json(f"{EUTILS_BASE}/esearch.fcgi", params=search_params)
        except HttpError as exc:
            print(f"  [PubMed] esearch error: {exc}")
            return []

        id_list = (res.get("esearchresult") or {}).get("idlist") or []
        if not id_list:
            return []

        time.sleep(0.35)
        summ_params = self._params({
            "db": "pubmed",
            "id": ",".join(id_list),
        })

        try:
            s_data = self.http.get_json(f"{EUTILS_BASE}/esummary.fcgi", params=summ_params)
        except HttpError as exc:
            print(f"  [PubMed] esummary error: {exc}")
            return []

        records = s_data.get("result") or {}
        candidates: List[PaperCandidate] = []

        for pmid in id_list:
            item = records.get(pmid)
            if not item or not isinstance(item, dict):
                continue

            title = clean_text(item.get("title"))
            authors = []
            for a in (item.get("authors") or []):
                if isinstance(a, dict) and a.get("name"):
                    authors.append(clean_text(a["name"]))
                elif isinstance(a, str):
                    authors.append(clean_text(a))

            doi = None
            pmc = None
            for aid in (item.get("articleids") or []):
                if isinstance(aid, dict):
                    id_type = aid.get("idtype")
                    val = aid.get("value")
                    if id_type == "doi":
                        doi = val
                    elif id_type in ("pmc", "pmcid"):
                        pmc = clean_pmcid(val)

            year = None
            pubdate = item.get("pubdate") or ""
            y_match = re.search(r"\b(19\d\d|20\d\d)\b", str(pubdate))
            if y_match:
                year = int(y_match.group(1))

            candidates.append(
                PaperCandidate(
                    title=title,
                    authors=authors,
                    journal=clean_text(item.get("source")),
                    year=year,
                    doi=doi,
                    pmid=pmid,
                    pmcid=pmc,
                    abstract=None,
                    is_open_access=bool(pmc),
                    source_db="pubmed",
                    source_queries=[f"pubmed:{query}"],
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    has_full_text_xml=bool(pmc),
                    raw_metadata=item,
                )
            )

        return candidates

    def search_pmc_oa(self, query: str, max_results: int = 10) -> List[PaperCandidate]:
        """Search PMC Open Access subset for full-text articles."""
        time.sleep(0.35)
        term = f"({query}) AND open access[filter]"
        search_params = self._params({
            "db": "pmc",
            "term": term,
            "retmax": max_results,
            "sort": "relevance",
        })

        try:
            res = self.http.get_json(f"{EUTILS_BASE}/esearch.fcgi", params=search_params)
        except HttpError as exc:
            print(f"  [PMC] esearch error: {exc}")
            return []

        id_list = (res.get("esearchresult") or {}).get("idlist") or []
        if not id_list:
            return []

        time.sleep(0.35)
        summ_params = self._params({
            "db": "pmc",
            "id": ",".join(id_list),
        })

        try:
            s_data = self.http.get_json(f"{EUTILS_BASE}/esummary.fcgi", params=summ_params)
        except HttpError as exc:
            print(f"  [PMC] esummary error: {exc}")
            return []

        records = s_data.get("result") or {}
        candidates: List[PaperCandidate] = []

        for uid in id_list:
            item = records.get(uid)
            if not item or not isinstance(item, dict):
                continue

            title = clean_text(item.get("title"))
            authors = []
            for a in (item.get("authors") or []):
                if isinstance(a, dict) and a.get("name"):
                    authors.append(clean_text(a["name"]))
                elif isinstance(a, str):
                    authors.append(clean_text(a))

            doi = None
            pmid = None
            pmcid = None
            for aid in (item.get("articleids") or []):
                if isinstance(aid, dict):
                    id_type = aid.get("idtype")
                    val = aid.get("value")
                    if id_type == "doi":
                        doi = val
                    elif id_type == "pmid":
                        pmid = val
                    elif id_type in ("pmc", "pmcid"):
                        pmcid = clean_pmcid(val)

            if not pmcid:
                pmcid = clean_pmcid(item.get("pmcid")) or f"PMC{uid}"

            year = None
            pubdate = item.get("pubdate") or ""
            y_match = re.search(r"\b(19\d\d|20\d\d)\b", str(pubdate))
            if y_match:
                year = int(y_match.group(1))

            candidates.append(
                PaperCandidate(
                    title=title,
                    authors=authors,
                    journal=clean_text(item.get("source")),
                    year=year,
                    doi=doi,
                    pmid=pmid,
                    pmcid=pmcid,
                    abstract=None,
                    is_open_access=True,
                    source_db="pmc",
                    source_queries=[f"pmc:{query}"],
                    url=f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
                    has_full_text_xml=True,
                    raw_metadata=item,
                )
            )

        return candidates

    def fetch_pmc_xml(self, pmcid: str) -> Optional[str]:
        time.sleep(0.35)
        clean_id = pmcid.upper().replace("PMC", "").strip()
        params = self._params({
            "db": "pmc",
            "id": clean_id,
            "retmode": "xml",
        })

        try:
            xml_text = self.http.get_text(f"{EUTILS_BASE}/efetch.fcgi", params=params)
            if "<article" in xml_text or "<pmc-articleset" in xml_text:
                return xml_text
        except HttpError as exc:
            print(f"  [PMC] efetch error for {pmcid}: {exc}")

        return None