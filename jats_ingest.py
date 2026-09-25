"""
jats_ingest.py
--------------
JATS/XML paper ingestion into ResearchDB with robust section classification
and memory-clearing DOM disposal.
"""

from __future__ import annotations

import gc
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Tuple


def lname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text_of(el: ET.Element) -> str:
    return re.sub(r"\s+", " ", " ".join(el.itertext())).strip()


def classify_section_title(title: str, current_key: str = "") -> str:
    low = title.lower()
    if any(w in low for w in ("method", "material", "experimental", "procedure", "protocol", "assay", "culture")):
        return "methods"
    if any(w in low for w in ("result", "finding", "effect", "response", "growth", "biomass", "expression", "accumulation", "analysis", "observation", "characterization")):
        return "results"
    if any(w in low for w in ("discussion", "perspective", "implication")):
        return "discussion"
    if any(w in low for w in ("intro", "background")):
        return "introduction"
    if any(w in low for w in ("conclusion", "summary", "concluding")):
        return "conclusion"
    if "limitation" in low:
        return "limitations"
    return current_key or "other"


def ingest_jats(db: Any, xml_path: str, research_question_id: int | None = None, source_query: str = "") -> int:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    title = ""
    abstract = ""
    pmid = pmcid = doi = None
    authors = []

    for el in root.iter():
        t = lname(el.tag)
        if t == "article-title" and not title:
            title = text_of(el)
        elif t == "abstract" and not abstract:
            abstract = text_of(el)
        elif t == "article-id":
            typ = el.attrib.get("pub-id-type")
            val = text_of(el)
            if typ == "pmid":
                pmid = val
            elif typ == "pmcid":
                pmcid = val
            elif typ == "doi":
                doi = val
        elif t == "name":
            sn = next((text_of(x) for x in el if lname(x.tag) == "surname"), "")
            gn = next((text_of(x) for x in el if lname(x.tag) == "given-names"), "")
            if sn:
                authors.append((gn + " " + sn).strip())

    paper = {
        "title": title,
        "authors": ", ".join(authors),
        "abstract": abstract,
        "pmid": pmid,
        "pmcid": pmcid,
        "doi": doi,
        "is_open_access": True,
        "full_text": None,
        "year": None,
    }
    pid = db.upsert_paper(research_question_id, paper, source_query=source_query)
    db.clear_paper_sections(pid)
    db.clear_paper_tables(pid)

    section_map = {
        "intro": "introduction", "introduction": "introduction",
        "methods": "methods", "materials|methods": "methods", "materials": "methods",
        "results": "results", "discussion": "discussion",
        "conclusions": "conclusion", "conclusion": "conclusion",
        "limitations": "limitations", "results_discussion": "results_discussion",
    }

    def walk_secs(parent, current=""):
        for sec in parent:
            if lname(sec.tag) != "sec":
                continue
            title_el = next((x for x in sec if lname(x.tag) == "title"), None)
            stitle = text_of(title_el) if title_el is not None else ""
            sec_type = sec.attrib.get("sec-type", "").lower()

            # 1. Attribute match
            key = section_map.get(sec_type) or section_map.get(re.sub(r"\s+", "_", stitle.lower()))
            # 2. Heuristic title match
            if not key:
                key = classify_section_title(stitle, current)

            direct = []
            for child in sec:
                ct = lname(child.tag)
                if ct in ("p", "disp-formula", "statement"):
                    txt = text_of(child)
                    if txt:
                        direct.append(txt)

            if direct:
                db.save_paper_section(pid, key, stitle, "\n".join(direct))

            for tbl in sec:
                if lname(tbl.tag) == "table-wrap":
                    save_table(db, pid, tbl)

            walk_secs(sec, key)

    def save_table(db, pid, tbl):
        label = next((text_of(x) for x in tbl if lname(x.tag) == "label"), "")
        cap = next((text_of(x) for x in tbl if lname(x.tag) == "caption"), "")
        table = next((x for x in tbl.iter() if lname(x.tag) == "table"), None)
        rows = []
        if table is not None:
            for tr in table.iter():
                if lname(tr.tag) == "tr":
                    rows.append([text_of(c) for c in tr if lname(c.tag) in ("th", "td")])
        if rows:
            db.save_paper_table(pid, label, cap, rows)

    body = next((x for x in root.iter() if lname(x.tag) == "body"), None)
    if body is not None:
        walk_secs(body)

    if abstract:
        db.save_paper_section(pid, "abstract", "Abstract", abstract)

    # MEMORY OPTIMIZATION: Clear and dereference DOM tree
    root.clear()
    del root, tree
    gc.collect()

    return pid
