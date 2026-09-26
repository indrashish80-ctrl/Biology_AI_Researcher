/**
 * Data models mirroring the Python engine's report JSON
 * (research_engine.investigate() dossier + SQLite schema).
 */

export type EffectDirection = "increase" | "decrease" | "no_effect" | "unclear";

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  journal: string;
  year: number;
  doi: string;
  pmid: string;
  pmcid: string | null;
  source_db: "pubmed" | "europe_pmc" | "pmc" | "crossref";
  is_open_access: boolean;
  relevance: number;
}

export interface Claim {
  id: string;
  paper_id: string;
  statement: string;
  quote: string;
  subject: string;
  organism: string;
  intervention: string;
  dose: string;
  measurement: string;
  effect_direction: EffectDirection;
  effect_size: number | null;
  p_value: number | null;
  sample_size: number | null;
  statistical_method: string | null;
  confidence: "high" | "medium" | "low";
}

export interface ConflictDifference {
  factor: string;
  a: string;
  b: string;
}

export interface Conflict {
  id: string;
  claim_a: string;
  claim_b: string;
  verdict: "contradiction" | "conflict" | "ambiguity";
  reasoning: string;
  differences: ConflictDifference[];
}

export interface MechanismChain {
  id: string;
  title: string;
  pathway: string[];
  evidence: string[];
  hops: number;
}

export interface Hypothesis {
  id: string;
  statement: string;
  mechanism: string;
  predictions: string[];
  required_measurement: string;
  expected_result: string;
  falsification_conditions: string[];
  next_experiment: string;
  status: "proposed" | "testing" | "supported" | "falsified";
}

export interface ResearchGap {
  id: string;
  description: string;
  category: string;
}

export interface GeoClosure {
  id: string;
  gse_accession: string;
  title: string;
  organism: string;
  n_samples: number;
  links_claims: string[];
  resolution: string;
}

export interface AuditFlag {
  id: string;
  severity: "info" | "warn" | "critical";
  target: string;
  message: string;
}

export interface EvidenceSummary {
  papers_analyzed: number;
  claims: number;
  evidence_anchors: number;
  conflict_groups: number;
  conflicting_pairs: number;
  hypotheses: number;
  research_gaps: number;
  audit_flags: number;
  geo_closures: number;
}

export interface Investigation {
  id: string;
  question: string;
  mode: "pipeline" | "agent";
  created_at: number;
  duration_ms: number;
  demo: boolean;
  summary: EvidenceSummary;
  papers: Paper[];
  claims: Claim[];
  conflicts: Conflict[];
  mechanisms: MechanismChain[];
  hypotheses: Hypothesis[];
  gaps: ResearchGap[];
  geo_closures: GeoClosure[];
  audit_flags: AuditFlag[];
  report_md?: string;
  answer?: string;
  raw_dossier?: unknown;
}

export type StageKey =
  | "retrieval"
  | "extraction"
  | "contradictions"
  | "geo"
  | "pathways"
  | "hypotheses"
  | "audit"
  | "report";

export interface StageInfo {
  key: StageKey;
  label: string;
  detail: string;
}

export const STAGES: StageInfo[] = [
  { key: "retrieval", label: "Literature acquisition", detail: "PubMed · Europe PMC · Crossref" },
  { key: "extraction", label: "Quote-grounded extraction", detail: "Claims anchored to verbatim quotes" },
  { key: "contradictions", label: "Contradiction detection", detail: "Cross-study directional analysis" },
  { key: "geo", label: "GEO loop closure", detail: "Empirical dataset resolution" },
  { key: "pathways", label: "Mechanistic synthesis", detail: "Multi-hop pathway construction" },
  { key: "hypotheses", label: "Hypothesis formulation", detail: "Falsifiable designs + gaps" },
  { key: "audit", label: "Adversarial audit", detail: "Deterministic red-team pass" },
  { key: "report", label: "Dossier assembly", detail: "Report + evidence dossier" },
];

export interface LogEvent {
  id: number;
  t: number;
  level: "info" | "warn" | "flag";
  message: string;
  stage?: string;
}

export type JobEvent =
  | { type: "stage"; stage: string; message: string; progress?: number }
  | { type: "log"; level: "info" | "warn" | "flag"; message: string }
  | { type: "done"; investigation: Investigation }
  | { type: "error"; message: string };

export interface Health {
  engine: string;
  providers: Record<string, boolean>;
  demo_mode: boolean;
}
