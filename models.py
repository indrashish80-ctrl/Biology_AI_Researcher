"""
retrieval/models.py
-------------------
Data models for source-controlled scientific literature retrieval.
Includes PMCID cleaning, HTML unescaping, and deduplication keys.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def clean_pmcid(pmcid: Optional[str]) -> Optional[str]:
    """
    Extract canonical PMCID (e.g., 'PMC-ID: PMC6528069;' -> 'PMC6528069').
    Guarantees valid filenames across Windows, macOS, and Linux.
    """
    if not pmcid:
        return None
    raw = str(pmcid).upper()
    m = re.search(r"PMC\s*(\d+)", raw)
    if m:
        return f"PMC{m.group(1)}"
    m_num = re.search(r"^\d+$", raw.strip())
    if m_num:
        return f"PMC{m_num.group(0)}"
    return None


def clean_text(text: Optional[str]) -> str:
    """Unescape XML/HTML entities (&lt;i&gt; -> <i>) and strip markup tags."""
    if not text:
        return ""
    t = html.unescape(str(text))
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", t).strip()


def clean_doi(doi: Optional[str]) -> Optional[str]:
    """Normalize DOI to lowercase without URL prefixes or trailing characters."""
    if not doi:
        return None
    d = html.unescape(str(doi).strip().lower())
    d = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", d)
    d = re.sub(r"\s+", "", d)
    return d.strip().rstrip(".")


def normalize_title(title: Optional[str]) -> str:
    if not title:
        return ""
    clean = clean_text(title).lower()
    clean = re.sub(r"[^a-z0-9]+", "", clean)
    return clean[:100]


@dataclass
class PaperCandidate:
    title: str
    authors: List[str] = field(default_factory=list)
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    abstract: Optional[str] = None
    is_open_access: bool = False
    source_db: str = ""  # "europe_pmc" | "pubmed" | "pmc" | "crossref"
    source_queries: List[str] = field(default_factory=list)
    url: Optional[str] = None
    has_full_text_xml: bool = False
    local_xml_path: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0

    def __post_init__(self):
        self.title = clean_text(self.title)
        if self.abstract:
            self.abstract = clean_text(self.abstract)
        if self.journal:
            self.journal = clean_text(self.journal)
        self.authors = [clean_text(a) for a in self.authors if a]

        if self.doi:
            self.doi = clean_doi(self.doi)
        if self.pmcid:
            self.pmcid = clean_pmcid(self.pmcid)
        if self.pmid:
            m_pmid = re.search(r"\d+", str(self.pmid))
            self.pmid = m_pmid.group(0) if m_pmid else None

    @property
    def dedup_key(self) -> str:
        """
        Hierarchical, deterministic deduplication key:
        1. DOI
        2. PMID
        3. PMCID
        4. Normalized title token
        """
        if self.doi:
            return f"doi:{self.doi}"
        if self.pmid:
            return f"pmid:{self.pmid}"
        if self.pmcid:
            return f"pmcid:{self.pmcid}"
        return f"title:{normalize_title(self.title)}"

    def merge_with(self, other: "PaperCandidate") -> None:
        """Merge complementary metadata from another database hit."""
        if not self.doi and other.doi:
            self.doi = other.doi
        if not self.pmid and other.pmid:
            self.pmid = other.pmid
        if not self.pmcid and other.pmcid:
            self.pmcid = other.pmcid
        if not self.abstract and other.abstract:
            self.abstract = other.abstract
        if not self.journal and other.journal:
            self.journal = other.journal
        if not self.year and other.year:
            self.year = other.year
        if not self.authors and other.authors:
            self.authors = other.authors
        if not self.is_open_access and other.is_open_access:
            self.is_open_access = other.is_open_access
        if not self.has_full_text_xml and other.has_full_text_xml:
            self.has_full_text_xml = other.has_full_text_xml
        if other.source_queries:
            for q in other.source_queries:
                if q not in self.source_queries:
                    self.source_queries.append(q)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dedup_key": self.dedup_key,
            "title": self.title,
            "authors": ", ".join(self.authors) if self.authors else None,
            "journal": self.journal,
            "year": self.year,
            "doi": self.doi,
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "abstract": self.abstract,
            "is_open_access": self.is_open_access,
            "source_db": self.source_db,
            "source_queries": self.source_queries,
            "url": self.url,
            "has_full_text_xml": self.has_full_text_xml,
            "local_xml_path": self.local_xml_path,
            "relevance_score": round(self.relevance_score, 3),
        }