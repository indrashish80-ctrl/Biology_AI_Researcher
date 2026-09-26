"""
database.py
-----------
SQLite research knowledge store.
Thread-safe connection enabled with check_same_thread=False.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from .core_utils import now_iso
except ImportError:
    from core_utils import now_iso

SCHEMA_VERSION = 1
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "research_knowledge.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS research_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_question_id INTEGER,
    dedup_key TEXT NOT NULL,
    title TEXT,
    authors TEXT,
    journal TEXT,
    year TEXT,
    doi TEXT,
    pmid TEXT,
    pmcid TEXT,
    abstract TEXT,
    full_text TEXT,
    is_open_access INTEGER,
    source_query TEXT,
    fetched_at TEXT NOT NULL,
    UNIQUE(dedup_key),
    FOREIGN KEY (research_question_id) REFERENCES research_questions(id)
);

CREATE TABLE IF NOT EXISTS paper_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL,
    organism TEXT,
    sample_size INTEGER,
    study_type TEXT,
    intervention TEXT,
    control TEXT,
    methods TEXT,
    outcomes_json TEXT,
    limitations_json TEXT,
    experimental_groups_json TEXT,
    measured_outcomes_json TEXT,
    raw_json TEXT,
    extraction_status TEXT NOT NULL,
    extracted_at TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);

CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_question_id INTEGER,
    source TEXT NOT NULL,
    accession TEXT NOT NULL,
    title TEXT,
    description TEXT,
    organism TEXT,
    url TEXT,
    metadata_json TEXT,
    discovered_at TEXT NOT NULL,
    UNIQUE(source, accession),
    FOREIGN KEY (research_question_id) REFERENCES research_questions(id)
);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_question_id INTEGER,
    dataset_path TEXT,
    group_column TEXT,
    outcome_column TEXT,
    evidence_record_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (research_question_id) REFERENCES research_questions(id)
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_question_id INTEGER,
    evidence_type TEXT NOT NULL,
    statement TEXT NOT NULL,
    source_type TEXT,
    source_id INTEGER,
    confidence TEXT,
    value_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (research_question_id) REFERENCES research_questions(id)
);

CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_question_id INTEGER,
    paper_id INTEGER,
    statement TEXT NOT NULL,
    subject TEXT,
    population TEXT,
    organism TEXT,
    intervention TEXT,
    dose TEXT,
    duration TEXT,
    measurement TEXT,
    statistical_method TEXT,
    effect_direction TEXT,
    effect_size REAL,
    p_value REAL,
    sample_size INTEGER,
    confidence_interval TEXT,
    conditions_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (research_question_id) REFERENCES research_questions(id),
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);

CREATE TABLE IF NOT EXISTS contradictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_question_id INTEGER,
    claim_a_id INTEGER NOT NULL,
    claim_b_id INTEGER NOT NULL,
    verdict TEXT NOT NULL,
    comparison_json TEXT,
    reasoning TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (claim_a_id) REFERENCES claims(id),
    FOREIGN KEY (claim_b_id) REFERENCES claims(id)
);

CREATE TABLE IF NOT EXISTS hypotheses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_question_id INTEGER,
    statement TEXT NOT NULL,
    mechanism TEXT,
    predictions_json TEXT,
    required_measurement TEXT,
    expected_result TEXT,
    falsification_conditions_json TEXT,
    supporting_evidence_json TEXT,
    competing_explanations_json TEXT,
    next_experiment TEXT,
    status TEXT NOT NULL DEFAULT 'proposed',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (research_question_id) REFERENCES research_questions(id)
);

CREATE TABLE IF NOT EXISTS experiment_designs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis_id INTEGER NOT NULL,
    design_json TEXT NOT NULL,
    power_notes TEXT,
    confounder_notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (hypothesis_id) REFERENCES hypotheses(id)
);

CREATE TABLE IF NOT EXISTS research_gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_question_id INTEGER,
    description TEXT NOT NULL,
    category TEXT,
    supporting_observation TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (research_question_id) REFERENCES research_questions(id)
);

CREATE TABLE IF NOT EXISTS provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    provenance_type TEXT NOT NULL,
    source_ref TEXT,
    details_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_question_id INTEGER,
    entity_type TEXT,
    entity_id INTEGER,
    claim_text TEXT,
    evidence_reference TEXT,
    issue TEXT NOT NULL,
    severity TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT NOT NULL,
    external_id TEXT NOT NULL,
    research_question_id INTEGER,
    processed_at TEXT NOT NULL,
    UNIQUE(item_type, external_id)
);

CREATE TABLE IF NOT EXISTS provider_health_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    event TEXT NOT NULL,
    latency_ms REAL,
    error_text TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_papers_rq ON papers(research_question_id);
CREATE INDEX IF NOT EXISTS idx_claims_rq ON claims(research_question_id);
CREATE INDEX IF NOT EXISTS idx_evidence_rq ON evidence(research_question_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_rq ON hypotheses(research_question_id);
CREATE INDEX IF NOT EXISTS idx_provenance_entity ON provenance(entity_type, entity_id);
"""


class ResearchDB:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DEFAULT_DB_PATH)
        # Thread safety fix: allow multi-threaded access
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(SCHEMA_SQL)
        self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS paper_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT, paper_id INTEGER NOT NULL,
            section_type TEXT NOT NULL, title TEXT, text TEXT NOT NULL,
            created_at TEXT NOT NULL, FOREIGN KEY (paper_id) REFERENCES papers(id)
        );
        CREATE INDEX IF NOT EXISTS idx_sections_paper ON paper_sections(paper_id);
        CREATE TABLE IF NOT EXISTS paper_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT, paper_id INTEGER NOT NULL,
            label TEXT, caption TEXT, rows_json TEXT, created_at TEXT NOT NULL,
            FOREIGN KEY (paper_id) REFERENCES papers(id)
        );
        CREATE INDEX IF NOT EXISTS idx_tables_paper ON paper_tables(paper_id);
        CREATE TABLE IF NOT EXISTS claim_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT, research_question_id INTEGER,
            group_key TEXT NOT NULL, intervention TEXT, outcome TEXT,
            member_ids_json TEXT, summary_json TEXT, explanations_json TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS biological_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, source_db TEXT NOT NULL,
            accession TEXT NOT NULL, symbol TEXT, name TEXT, organism TEXT, metadata_json TEXT,
            UNIQUE(entity_type, source_db, accession)
        );
        CREATE TABLE IF NOT EXISTS entity_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, from_entity_id INTEGER NOT NULL, relation TEXT NOT NULL,
            to_entity_id INTEGER NOT NULL, source_db TEXT, created_at TEXT NOT NULL,
            UNIQUE(from_entity_id, relation, to_entity_id, source_db)
        );
        CREATE TABLE IF NOT EXISTS entity_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, entity_id INTEGER NOT NULL, source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL, mention TEXT, created_at TEXT NOT NULL,
            UNIQUE(entity_id, source_type, source_id, mention)
        );
        """)
        for col, typ in (("evidence_origin", "TEXT"), ("grounded", "INTEGER"), ("grounding_score", "REAL"),
                         ("quote", "TEXT"), ("flags_json", "TEXT"), ("nonsignificant_direction", "INTEGER"),
                         ("study_design", "TEXT")):
            try:
                self._conn.execute(f"ALTER TABLE claims ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass
        self._conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _row(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        return dict(row) if row is not None else None

    def _rows(self, rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
        return [dict(r) for r in rows]

    def _insert(self, table: str, fields: Dict[str, Any]) -> int:
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        cursor = self._conn.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            tuple(fields.values()),
        )
        self._conn.commit()
        return cursor.lastrowid

    @staticmethod
    def _j(value: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _dj(value: Optional[str]) -> Any:
        if value in (None, ""):
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None

    # ------------------------------------------------------
    # RESEARCH QUESTIONS
    # ------------------------------------------------------

    def create_research_question(self, question: str) -> int:
        existing = self._row(
            self._conn.execute(
                "SELECT * FROM research_questions WHERE question = ? ORDER BY id DESC LIMIT 1",
                (question,),
            ).fetchone()
        )
        if existing:
            return existing["id"]

        ts = now_iso()
        return self._insert(
            "research_questions",
            {"question": question, "status": "open", "created_at": ts, "updated_at": ts},
        )

    def get_research_question(self, rq_id: int) -> Optional[Dict[str, Any]]:
        return self._row(
            self._conn.execute("SELECT * FROM research_questions WHERE id = ?", (rq_id,)).fetchone()
        )

    # ------------------------------------------------------
    # PAPERS
    # ------------------------------------------------------

    def upsert_paper(self, research_question_id: Optional[int], paper: Dict[str, Any], source_query: str = "") -> int:
        dedup_key = (
            paper.get("doi")
            or paper.get("pmid")
            or paper.get("pmcid")
            or f"title::{(paper.get('title') or '').strip().lower()}"
        )
        existing = self._row(
            self._conn.execute("SELECT id FROM papers WHERE dedup_key = ?", (dedup_key,)).fetchone()
        )
        if existing:
            return existing["id"]

        return self._insert(
            "papers",
            {
                "research_question_id": research_question_id,
                "dedup_key": dedup_key,
                "title": paper.get("title"),
                "authors": paper.get("authors"),
                "journal": paper.get("journal"),
                "year": str(paper.get("year")) if paper.get("year") is not None else None,
                "doi": paper.get("doi"),
                "pmid": paper.get("pmid"),
                "pmcid": paper.get("pmcid"),
                "abstract": paper.get("abstract"),
                "full_text": paper.get("full_text"),
                "is_open_access": 1 if paper.get("is_open_access") else 0,
                "source_query": source_query,
                "fetched_at": now_iso(),
            },
        )

    def get_paper(self, paper_id: int) -> Optional[Dict[str, Any]]:
        return self._row(self._conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone())

    def list_papers(self, research_question_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if research_question_id is None:
            return self._rows(self._conn.execute("SELECT * FROM papers").fetchall())
        return self._rows(
            self._conn.execute(
                "SELECT * FROM papers WHERE research_question_id = ?", (research_question_id,)
            ).fetchall()
        )

    def list_papers_summary(self, research_question_id: Optional[int] = None) -> List[Dict[str, Any]]:
        cols = "id, research_question_id, dedup_key, title, journal, year, doi, pmid, pmcid, is_open_access"
        if research_question_id is None:
            return self._rows(self._conn.execute(f"SELECT {cols} FROM papers").fetchall())
        return self._rows(
            self._conn.execute(
                f"SELECT {cols} FROM papers WHERE research_question_id = ?", (research_question_id,)
            ).fetchall()
        )

    def save_paper_extraction(self, paper_id: int, extraction: Dict[str, Any], status: str = "validated") -> int:
        study = extraction.get("study", {}) if isinstance(extraction.get("study"), dict) else {}
        return self._insert(
            "paper_extractions",
            {
                "paper_id": paper_id,
                "organism": study.get("organism") or extraction.get("organism"),
                "sample_size": study.get("sample_size") or extraction.get("sample_size"),
                "study_type": study.get("study_type") or extraction.get("study_type"),
                "intervention": extraction.get("intervention"),
                "control": extraction.get("control"),
                "methods": extraction.get("methods"),
                "outcomes_json": self._j(extraction.get("outcomes")),
                "limitations_json": self._j(extraction.get("limitations")),
                "experimental_groups_json": self._j(extraction.get("experimental_groups")),
                "measured_outcomes_json": self._j(extraction.get("measured_outcomes")),
                "raw_json": self._j(extraction),
                "extraction_status": status,
                "extracted_at": now_iso(),
            },
        )

    def get_paper_extraction(self, paper_id: int) -> Optional[Dict[str, Any]]:
        row = self._row(
            self._conn.execute(
                "SELECT * FROM paper_extractions WHERE paper_id = ? ORDER BY id DESC LIMIT 1", (paper_id,)
            ).fetchone()
        )
        if not row:
            return None
        for key in ("outcomes_json", "limitations_json", "experimental_groups_json", "measured_outcomes_json", "raw_json"):
            row[key.replace("_json", "")] = self._dj(row[key])
        return row

    def save_paper_section(self, paper_id: int, section_type: str, title: str, text: str) -> int:
        return self._insert("paper_sections", {"paper_id": paper_id, "section_type": section_type,
            "title": title, "text": text, "created_at": now_iso()})

    def clear_paper_sections(self, paper_id: int) -> None:
        self._conn.execute("DELETE FROM paper_sections WHERE paper_id = ?", (paper_id,)); self._conn.commit()

    def get_sections(self, paper_id: int) -> List[Dict[str, Any]]:
        return self._rows(self._conn.execute("SELECT * FROM paper_sections WHERE paper_id = ? ORDER BY id", (paper_id,)).fetchall())

    def save_paper_table(self, paper_id: int, label: str, caption: str, rows: List[List[str]]) -> int:
        return self._insert("paper_tables", {"paper_id": paper_id, "label": label, "caption": caption,
            "rows_json": self._j(rows), "created_at": now_iso()})

    def clear_paper_tables(self, paper_id: int) -> None:
        self._conn.execute("DELETE FROM paper_tables WHERE paper_id = ?", (paper_id,)); self._conn.commit()

    def get_tables(self, paper_id: int) -> List[Dict[str, Any]]:
        rows = self._rows(self._conn.execute("SELECT * FROM paper_tables WHERE paper_id = ? ORDER BY id", (paper_id,)).fetchall())
        for r in rows: r["rows"] = self._dj(r.pop("rows_json")) or []
        return rows

    def save_paper_extraction_ext(self, paper_id: int, extraction: Dict[str, Any], status: str = "validated", basis: str = "full_text") -> int:
        eid = self.save_paper_extraction(paper_id, extraction, status=status)
        self._conn.execute("UPDATE paper_extractions SET raw_json = ? WHERE id = ?", (self._j({**extraction, "basis": basis}), eid)); self._conn.commit()
        return eid

    def get_extraction_raw(self, paper_id: int) -> Dict[str, Any]:
        row = self.get_paper_extraction(paper_id)
        return (row or {}).get("raw") or {}

    # ------------------------------------------------------
    # EVIDENCE
    # ------------------------------------------------------

    def add_evidence(self, research_question_id: Optional[int], evidence_type: str, statement: str,
                      source_type: Optional[str] = None, source_id: Optional[int] = None,
                      confidence: Optional[str] = None, value: Any = None) -> int:
        eid = self._insert(
            "evidence",
            {
                "research_question_id": research_question_id,
                "evidence_type": evidence_type,
                "statement": statement,
                "source_type": source_type,
                "source_id": source_id,
                "confidence": confidence,
                "value_json": self._j(value),
                "created_at": now_iso(),
            },
        )
        self.add_provenance("evidence", eid, evidence_type, source_ref=f"{source_type}:{source_id}" if source_type else None)
        return eid

    def list_evidence(self, research_question_id: Optional[int] = None) -> List[Dict[str, Any]]:
        rows = (
            self._rows(self._conn.execute("SELECT * FROM evidence").fetchall())
            if research_question_id is None
            else self._rows(
                self._conn.execute(
                    "SELECT * FROM evidence WHERE research_question_id = ?", (research_question_id,)
                ).fetchall()
            )
        )
        for row in rows:
            row["value"] = self._dj(row["value_json"])
        return rows

    # ------------------------------------------------------
    # CLAIMS
    # ------------------------------------------------------

    def add_claim(self, research_question_id: Optional[int], paper_id: Optional[int], claim: Dict[str, Any]) -> int:
        claim = dict(claim)
        claim.setdefault("effect_direction", claim.get("direction"))
        claim.setdefault("measurement", claim.get("outcome"))
        cid = self._insert(
            "claims",
            {
                "research_question_id": research_question_id,
                "paper_id": paper_id,
                "statement": claim.get("statement", ""),
                "subject": claim.get("subject"),
                "population": claim.get("population"),
                "organism": claim.get("organism"),
                "intervention": claim.get("intervention"),
                "dose": claim.get("dose"),
                "duration": claim.get("duration"),
                "measurement": claim.get("measurement"),
                "statistical_method": claim.get("statistical_method"),
                "effect_direction": claim.get("effect_direction"),
                "effect_size": claim.get("effect_size"),
                "p_value": claim.get("p_value"),
                "sample_size": claim.get("sample_size"),
                "confidence_interval": self._j(claim.get("confidence_interval")),
                "conditions_json": self._j(claim.get("conditions")),
                "created_at": now_iso(),
            },
        )
        source_ref = f"paper:{paper_id}" if paper_id else "unknown"
        self.add_provenance("claim", cid, "REPORTED_BY_PAPER" if paper_id else "AI_INFERENCE", source_ref=source_ref)
        return cid

    def add_claim_ext(self, research_question_id: Optional[int], paper_id: Optional[int], claim: Dict[str, Any]) -> int:
        cid = self.add_claim(research_question_id, paper_id, claim)
        self._conn.execute("""UPDATE claims SET evidence_origin=?, grounded=?, grounding_score=?, quote=?, flags_json=?,
            nonsignificant_direction=?, study_design=? WHERE id=?""",
            (claim.get("evidence_origin"), int(bool(claim.get("grounded"))), claim.get("grounding_score"),
             claim.get("quote"), self._j(claim.get("flags")), int(bool(claim.get("nonsignificant_direction"))),
             claim.get("study_design"), cid)); self._conn.commit()
        return cid

    def delete_claims_for_paper(self, paper_id: int) -> None:
        self._conn.execute("DELETE FROM claims WHERE paper_id = ?", (paper_id,)); self._conn.commit()

    def claims_for_paper(self, paper_id: int) -> List[Dict[str, Any]]:
        return self._claims_query("SELECT * FROM claims WHERE paper_id = ? ORDER BY id", (paper_id,))

    def claims_with_papers(self, research_question_id: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = "SELECT c.*, p.title AS paper_title, p.pmid, p.pmcid, p.doi FROM claims c LEFT JOIN papers p ON p.id=c.paper_id"
        args = ()
        if research_question_id is not None:
            sql += " WHERE c.research_question_id = ?"
            args = (research_question_id,)
        sql += " ORDER BY c.id"
        return self._claims_query(sql, args)

    def _claims_query(self, sql: str, args: tuple) -> List[Dict[str, Any]]:
        rows = self._rows(self._conn.execute(sql, args).fetchall())
        for r in rows:
            r["conditions"] = self._dj(r.get("conditions_json"))
            r["confidence_interval"] = self._dj(r.get("confidence_interval"))
            r["flags"] = self._dj(r.get("flags_json")) or []
            r["grounded"] = bool(r.get("grounded"))
        return rows

    # ------------------------------------------------------
    # CONTRADICTIONS
    # ------------------------------------------------------

    def add_contradiction(self, research_question_id: Optional[int], claim_a_id: int, claim_b_id: int,
                           verdict: str, comparison: Dict[str, Any], reasoning: str = "") -> int:
        return self._insert(
            "contradictions",
            {
                "research_question_id": research_question_id,
                "claim_a_id": claim_a_id,
                "claim_b_id": claim_b_id,
                "verdict": verdict,
                "comparison_json": self._j(comparison),
                "reasoning": reasoning,
                "created_at": now_iso(),
            },
        )

    def list_contradictions(self, research_question_id: Optional[int] = None) -> List[Dict[str, Any]]:
        rows = (
            self._rows(self._conn.execute("SELECT * FROM contradictions").fetchall())
            if research_question_id is None
            else self._rows(
                self._conn.execute(
                    "SELECT * FROM contradictions WHERE research_question_id = ?", (research_question_id,)
                ).fetchall()
            )
        )
        for row in rows:
            row["comparison"] = self._dj(row["comparison_json"])
        return rows

    # ------------------------------------------------------
    # HYPOTHESES & EXPERIMENT DESIGNS
    # ------------------------------------------------------

    def clear_contradictions(self, research_question_id: Optional[int] = None) -> None:
        """Delete stored contradiction records (used before re-running detection)."""
        if research_question_id is None:
            self._conn.execute("DELETE FROM contradictions")
        else:
            self._conn.execute(
                "DELETE FROM contradictions WHERE research_question_id = ?", (research_question_id,)
            )
        self._conn.commit()

    def save_claim_group(self, research_question_id: Optional[int], group_key: str, intervention: str,
                         outcome: str, member_ids: List[int], summary: Dict[str, Any],
                         explanations: List[Any]) -> int:
        """Persist a grouped set of claims (same intervention/outcome) used for
        cross-study contradiction analysis and GEO loop-closure targeting."""
        cur = self._conn.execute(
            "INSERT INTO claim_groups (research_question_id, group_key, intervention, outcome, "
            "member_ids_json, summary_json, explanations_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                research_question_id,
                group_key,
                intervention,
                outcome,
                self._j(member_ids),
                self._j(summary),
                self._j(explanations),
                now_iso(),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def add_experiment_design(self, hypothesis_id: int, design: Dict[str, Any],
                              power_notes: str = "", confounder_notes: str = "") -> int:
        """Attach a proposed experimental design/specification to a hypothesis."""
        cur = self._conn.execute(
            "INSERT INTO experiment_designs (hypothesis_id, design_json, power_notes, "
            "confounder_notes, created_at) VALUES (?, ?, ?, ?, ?)",
            (hypothesis_id, self._j(design), power_notes, confounder_notes, now_iso()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def log_provider_event(self, provider: str, event: str,
                           latency_ms: Optional[float] = None, error_text: Optional[str] = None) -> None:
        """Record a provider health event (success / 429 / cooldown / hard error)."""
        self._conn.execute(
            "INSERT INTO provider_health_log (provider, event, latency_ms, error_text, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (provider, event, latency_ms, error_text, now_iso()),
        )
        self._conn.commit()

    def update_hypothesis_status(self, hypothesis_id: int, new_status: str) -> None:
        """Update a hypothesis lifecycle status (proposed / supported / refuted ...)."""
        self._conn.execute(
            "UPDATE hypotheses SET status = ? WHERE id = ?", (new_status, hypothesis_id)
        )
        self._conn.commit()

    def upsert_dataset(self, research_question_id: Optional[int], source: str, accession: str,
                       title: str = "", description: str = "", organism: str = "",
                       url: str = "", metadata: Optional[Dict[str, Any]] = None) -> int:
        """Insert or update a discovered public dataset (GEO/SRA) record."""
        existing = self._conn.execute(
            "SELECT id FROM datasets WHERE source = ? AND accession = ?", (source, accession)
        ).fetchone()
        created = now_iso()
        if existing:
            self._conn.execute(
                "UPDATE datasets SET research_question_id = ?, title = ?, description = ?, "
                "organism = ?, url = ?, metadata_json = ? WHERE id = ?",
                (research_question_id, title, description, organism, url, self._j(metadata or {}), existing[0]),
            )
            self._conn.commit()
            return int(existing[0])
        cur = self._conn.execute(
            "INSERT INTO datasets (research_question_id, source, accession, title, description, "
            "organism, url, metadata_json, discovered_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (research_question_id, source, accession, title, description, organism, url,
             self._j(metadata or {}), created),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def add_hypothesis(self, research_question_id: Optional[int], hypothesis: Dict[str, Any]) -> int:
        ts = now_iso()
        hid = self._insert(
            "hypotheses",
            {
                "research_question_id": research_question_id,
                "statement": hypothesis.get("statement", ""),
                "mechanism": hypothesis.get("mechanism"),
                "predictions_json": self._j(hypothesis.get("predictions")),
                "required_measurement": hypothesis.get("required_measurement"),
                "expected_result": hypothesis.get("expected_result"),
                "falsification_conditions_json": self._j(hypothesis.get("falsification_conditions")),
                "supporting_evidence_json": self._j(hypothesis.get("supporting_evidence")),
                "competing_explanations_json": self._j(hypothesis.get("competing_explanations")),
                "next_experiment": hypothesis.get("next_experiment"),
                "status": hypothesis.get("status", "proposed"),
                "created_at": ts,
                "updated_at": ts,
            },
        )
        self.add_provenance("hypothesis", hid, "HYPOTHESIS", source_ref="ai_inference")
        return hid

    def list_hypotheses(self, research_question_id: Optional[int] = None) -> List[Dict[str, Any]]:
        rows = (
            self._rows(self._conn.execute("SELECT * FROM hypotheses").fetchall())
            if research_question_id is None
            else self._rows(
                self._conn.execute(
                    "SELECT * FROM hypotheses WHERE research_question_id = ?", (research_question_id,)
                ).fetchall()
            )
        )
        for row in rows:
            for field in ("predictions", "falsification_conditions", "supporting_evidence", "competing_explanations"):
                row[field] = self._dj(row.get(f"{field}_json"))
        return rows

    def add_research_gap(self, research_question_id: Optional[int], description: str,
                          category: str = "", supporting_observation: str = "") -> int:
        return self._insert(
            "research_gaps",
            {
                "research_question_id": research_question_id,
                "description": description,
                "category": category,
                "supporting_observation": supporting_observation,
                "created_at": now_iso(),
            },
        )

    def list_research_gaps(self, research_question_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if research_question_id is None:
            return self._rows(self._conn.execute("SELECT * FROM research_gaps").fetchall())
        return self._rows(
            self._conn.execute(
                "SELECT * FROM research_gaps WHERE research_question_id = ?", (research_question_id,)
            ).fetchall()
        )

    # ------------------------------------------------------
    # BIOLOGICAL ENTITIES
    # ------------------------------------------------------

    def upsert_entity(self, entity_type: str, source_db: str, accession: str, symbol: str = "", name: str = "",
                      organism: str = "", metadata: Any = None) -> int:
        row = self._row(self._conn.execute("SELECT id FROM biological_entities WHERE entity_type=? AND source_db=? AND accession=?",
            (entity_type, source_db, accession)).fetchone())
        if row:
            self._conn.execute("UPDATE biological_entities SET symbol=?, name=?, organism=?, metadata_json=? WHERE id=?",
                (symbol, name, organism, self._j(metadata), row["id"]))
            self._conn.commit()
            return row["id"]
        return self._insert("biological_entities", {"entity_type": entity_type, "source_db": source_db, "accession": accession,
            "symbol": symbol, "name": name, "organism": organism, "metadata_json": self._j(metadata)})

    def link_entity(self, entity_id: int, source_type: str, source_id: int, mention: str = "") -> int:
        row = self._row(self._conn.execute("SELECT id FROM entity_mentions WHERE entity_id=? AND source_type=? AND source_id=? AND mention=?",
            (entity_id, source_type, source_id, mention)).fetchone())
        if row: return row["id"]
        return self._insert("entity_mentions", {"entity_id": entity_id, "source_type": source_type, "source_id": source_id,
            "mention": mention, "created_at": now_iso()})

    # ------------------------------------------------------
    # PROVENANCE, AUDIT, MEMORY
    # ------------------------------------------------------

    def add_provenance(self, entity_type: str, entity_id: int, provenance_type: str,
                        source_ref: Optional[str] = None, details: Any = None) -> int:
        return self._insert(
            "provenance",
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "provenance_type": provenance_type,
                "source_ref": source_ref,
                "details_json": self._j(details),
                "created_at": now_iso(),
            },
        )

    def add_audit_flag(self, research_question_id: Optional[int], entity_type: str, entity_id: Optional[int],
                        claim_text: str, evidence_reference: str, issue: str, severity: str = "HIGH") -> int:
        return self._insert(
            "audit_flags",
            {
                "research_question_id": research_question_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "claim_text": claim_text,
                "evidence_reference": evidence_reference,
                "issue": issue,
                "severity": severity,
                "created_at": now_iso(),
            },
        )

    def list_audit_flags(self, research_question_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if research_question_id is None:
            return self._rows(self._conn.execute("SELECT * FROM audit_flags").fetchall())
        return self._rows(
            self._conn.execute(
                "SELECT * FROM audit_flags WHERE research_question_id = ?", (research_question_id,)
            ).fetchall()
        )

    def already_processed(self, item_type: str, external_id: str) -> bool:
        if not external_id:
            return False
        row = self._conn.execute(
            "SELECT id FROM processed_items WHERE item_type = ? AND external_id = ?",
            (item_type, external_id),
        ).fetchone()
        return row is not None

    def mark_processed(self, item_type: str, external_id: str, research_question_id: Optional[int] = None) -> None:
        if not external_id:
            return
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO processed_items (item_type, external_id, research_question_id, processed_at) "
                "VALUES (?, ?, ?, ?)",
                (item_type, external_id, research_question_id, now_iso()),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            pass

    def research_question_summary(self, rq_id: int) -> Dict[str, Any]:
        def count(table: str) -> int:
            return self._conn.execute(
                f"SELECT COUNT(*) as n FROM {table} WHERE research_question_id = ?", (rq_id,)
            ).fetchone()["n"]

        return {
            "research_question": self.get_research_question(rq_id),
            "papers": count("papers"),
            "evidence": count("evidence"),
            "claims": count("claims"),
            "contradictions": count("contradictions"),
            "hypotheses": count("hypotheses"),
            "research_gaps": count("research_gaps"),
            "audit_flags": count("audit_flags"),
        }