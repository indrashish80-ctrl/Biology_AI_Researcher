"""
retrieval package
-----------------
Controlled, source-restricted retrieval layer for the biology research AI.
"""

from retrieval.crossref import CrossrefClient
from retrieval.europe_pmc import EuropePMCClient
from retrieval.models import PaperCandidate
from retrieval.pubmed import PubMedClient
from retrieval.source_manager import SourceManager

__all__ = [
    "PaperCandidate",
    "EuropePMCClient",
    "PubMedClient",
    "CrossrefClient",
    "SourceManager",
]