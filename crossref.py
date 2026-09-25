"""
retrieval/crossref.py
---------------------
Crossref client for broad scholarly metadata discovery.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from http_client import HttpClient, HttpError
from retrieval.models import PaperCandidate, clean_doi, clean_text

CROSSREF_BASE = "https://api.crossref.org/works"


class CrossrefClient:
    def __init__(self, http: Optional[HttpClient] = None):
        self.http = http or HttpClient(
            cache_dir="cache/retrieval/crossref",
            user_agent="BiologyAIResearcher/1.0 (mailto:biology-pipeline@example.org)",
        )

    def search(self, query: str, max_results: int = 10) -> List[PaperCandidate]:
        """Query Crossref Works API and return clean candidate papers."""
        params = {
            "query.bibliographic": query,
            "rows": str(max_results),
            "select": "DOI,title,author,container-title,published,abstract,URL,is-referenced-by-count,license",
        }

        try:
            data = self.http.get_json(CROSSREF_BASE, params=params)
        except HttpError as exc:
            print(f"  [Crossref] search error: {exc}")
            return []

        items = (data.get("message") or {}).get("items") or []
        candidates: List[PaperCandidate] = []

        for it in items:
            if not isinstance(it, dict):
                continue
            raw_titles = it.get("title") or []
            title = clean_text(raw_titles[0]) if (isinstance(raw_titles, list) and raw_titles) else ""
            if not title:
                continue

            authors = []
            for a in (it.get("author") or []):
                if isinstance(a, dict):
                    name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                    if name:
                        authors.append(clean_text(name))

            journals = it.get("container-title") or []
            journal = clean_text(journals[0]) if (isinstance(journals, list) and journals) else None

            year = None
            date_parts = (it.get("published") or {}).get("date-parts") or [[]]
            if date_parts and isinstance(date_parts[0], list) and date_parts[0]:
                try:
                    year = int(date_parts[0][0])
                except (ValueError, IndexError):
                    pass

            raw_abstract = it.get("abstract")
            abstract = clean_text(raw_abstract) if raw_abstract else None

            is_oa = False
            for lic in (it.get("license") or []):
                if isinstance(lic, dict):
                    url = str(lic.get("URL", "")).lower()
                    if "creativecommons" in url or "open" in url:
                        is_oa = True
                        break

            cand = PaperCandidate(
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                doi=clean_doi(it.get("DOI")),
                abstract=abstract,
                is_open_access=is_oa,
                source_db="crossref",
                source_queries=[f"crossref:{query}"],
                url=it.get("URL") or (f"https://doi.org/{it.get('DOI')}" if it.get("DOI") else None),
                has_full_text_xml=False,
                raw_metadata={"cited_by_count": it.get("is-referenced-by-count")},
            )
            candidates.append(cand)

        return candidates