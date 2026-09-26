import type {
  AuditFlag,
  Claim,
  Conflict,
  GeoClosure,
  Hypothesis,
  Investigation,
  LogEvent,
  MechanismChain,
  Paper,
  ResearchGap,
  StageKey,
} from "./types";

/**
 * Demo dataset replicating the engine's report shape so the console is fully
 * explorable without GROQ_API_KEY / live NCBI access. Content mirrors a
 * canonical question the engine handles well: hypoxia signaling vs HIF-1α.
 */

export const DEMO_PAPERS: Paper[] = [
  {
    id: "p1",
    title: "Intermittent hypoxia induces HIF-1α stabilization and blunts insulin signaling in murine skeletal muscle",
    authors: ["R. Kojima", "A. Delgado", "P. Nørgaard"],
    journal: "Journal of Applied Physiology",
    year: 2021,
    doi: "10.1152/japplphysiol.00123.2021",
    pmid: "33888521",
    pmcid: "PMC8123456",
    source_db: "europe_pmc",
    is_open_access: true,
    relevance: 0.94,
  },
  {
    id: "p2",
    title: "Chronic sustained hypoxia improves glucose tolerance through AMPK-dependent glucose uptake in mice",
    authors: ["L. Moretti", "S. Bhatt", "H. Chen"],
    journal: "Diabetes",
    year: 2019,
    doi: "10.2337/db18-1102",
    pmid: "30918044",
    pmcid: null,
    source_db: "pubmed",
    is_open_access: false,
    relevance: 0.91,
  },
  {
    id: "p3",
    title: "Hypoxic preconditioning attenuates hepatic insulin resistance in a diet-induced obesity model",
    authors: ["T. Yamagishi", "E. Voss", "K. Aitken"],
    journal: "Hepatology Communications",
    year: 2022,
    doi: "10.1002/hep4.1933",
    pmid: "35495781",
    pmcid: "PMC9051234",
    source_db: "pmc",
    is_open_access: true,
    relevance: 0.88,
  },
  {
    id: "p4",
    title: "Dose-dependent effects of inspired oxygen fraction on skeletal muscle mitochondrial biogenesis",
    authors: ["N. Okafor", "M. Lindqvist"],
    journal: "American Journal of Physiology-Endocrinology and Metabolism",
    year: 2020,
    doi: "10.1152/ajpendo.00441.2019",
    pmid: "32049177",
    pmcid: null,
    source_db: "europe_pmc",
    is_open_access: false,
    relevance: 0.83,
  },
  {
    id: "p5",
    title: "HIF-1α activation and insulin signaling compete for mTOR capacity under prolonged hypoxia",
    authors: ["V. Argyropoulos", "D. Whitfield", "J. Mbeki", "C. Rojas"],
    journal: "Cell Metabolism Reports",
    year: 2023,
    doi: "10.1016/j.cmetr.2023.100174",
    pmid: "37012009",
    pmcid: "PMC9988776",
    source_db: "europe_pmc",
    is_open_access: true,
    relevance: 0.9,
  },
  {
    id: "p6",
    title: "Intermittent versus sustained hypoxia: divergent metabolic outcomes in male Wistar rats",
    authors: ["F. Duarte", "G. Ivanov"],
    journal: "Respiratory Physiology & Neurobiology",
    year: 2018,
    doi: "10.1016/j.resp.2018.04.007",
    pmid: "29678732",
    pmcid: null,
    source_db: "crossref",
    is_open_access: false,
    relevance: 0.79,
  },
];

export const DEMO_CLAIMS: Claim[] = [
  {
    id: "c1",
    paper_id: "p1",
    statement:
      "Six weeks of intermittent hypoxia (FIO2 5–10% cycles) stabilized HIF-1α in murine skeletal muscle and impaired insulin-stimulated AKT phosphorylation.",
    quote:
      "Intermittent hypoxia exposure significantly increased nuclear HIF-1α (2.7-fold, p = 0.004) and reduced insulin-stimulated AKT Ser473 phosphorylation by 38% relative to normoxic controls (p = 0.011).",
    subject: "skeletal muscle insulin signaling",
    organism: "mouse (C57BL/6J)",
    intervention: "intermittent hypoxia, 8h/day",
    dose: "FIO2 5–10% cycles",
    measurement: "pAKT Ser473 / total AKT",
    effect_direction: "decrease",
    effect_size: -0.38,
    p_value: 0.011,
    sample_size: 12,
    statistical_method: "two-tailed t-test",
    confidence: "high",
  },
  {
    id: "c2",
    paper_id: "p2",
    statement:
      "Chronic sustained hypoxia (10% O2, 4 weeks) improved glucose tolerance in mice via AMPK-dependent GLUT4 translocation.",
    quote:
      "Sustained hypoxic mice showed improved glucose tolerance (AUC reduced 21%, p = 0.002) and 1.8-fold higher membrane GLUT4, abolished by compound C (AMPK inhibitor).",
    subject: "whole-body glucose tolerance",
    organism: "mouse (C57BL/6J)",
    intervention: "sustained hypoxia, 4 weeks",
    dose: "FIO2 10% continuous",
    measurement: "GTT AUC",
    effect_direction: "increase",
    effect_size: -0.21,
    p_value: 0.002,
    sample_size: 10,
    statistical_method: "one-way ANOVA + Tukey",
    confidence: "high",
  },
  {
    id: "c3",
    paper_id: "p3",
    statement:
      "Hypoxic preconditioning attenuated hepatic insulin resistance in diet-induced obesity without measurable HIF-1α nuclear accumulation.",
    quote:
      "Hepatic HOMA-IR fell from 6.1 to 4.2 (p = 0.03) after preconditioning, with no detectable increase in nuclear HIF-1α (p = 0.44).",
    subject: "hepatic insulin resistance",
    organism: "mouse (DIO model)",
    intervention: "hypoxic preconditioning, 5% O2, 3h pulses",
    dose: "FIO2 5% intermittent",
    measurement: "HOMA-IR",
    effect_direction: "decrease",
    effect_size: -0.31,
    p_value: 0.03,
    sample_size: 8,
    statistical_method: "paired t-test",
    confidence: "medium",
  },
  {
    id: "c4",
    paper_id: "p4",
    statement:
      "Mitochondrial biogenesis in skeletal muscle responds non-monotonically to inspired oxygen fraction, peaking at mild hypoxia.",
    quote:
      "PGC-1α expression peaked at FIO2 15% (1.6-fold vs 21%, p = 0.019) and declined at 10% (0.9-fold, p = 0.61 vs normoxia).",
    subject: "mitochondrial biogenesis",
    organism: "mouse (C57BL/6J)",
    intervention: "graded sustained hypoxia, 2 weeks",
    dose: "FIO2 10/15/21%",
    measurement: "PGC-1α mRNA",
    effect_direction: "no_effect",
    effect_size: 0.0,
    p_value: 0.61,
    sample_size: 9,
    statistical_method: "linear mixed model",
    confidence: "high",
  },
  {
    id: "c5",
    paper_id: "p5",
    statement:
      "Under prolonged hypoxia, HIF-1α activation and insulin signaling compete for limited mTOR capacity, producing biphasic metabolic effects.",
    quote:
      "Rapamycin rescued insulin sensitivity under prolonged hypoxia (p = 0.006), consistent with mTOR-mediated competition between HIF-1α translation and IRS-1 signaling.",
    subject: "mTOR-mediated signaling competition",
    organism: "mouse (C57BL/6J)",
    intervention: "sustained hypoxia + rapamycin",
    dose: "FIO2 8%, 14 days",
    measurement: "IRS-1 associated PI3K activity",
    effect_direction: "increase",
    effect_size: 0.44,
    p_value: 0.006,
    sample_size: 11,
    statistical_method: "two-way ANOVA",
    confidence: "high",
  },
  {
    id: "c6",
    paper_id: "p6",
    statement:
      "Intermittent but not sustained hypoxia elevated fasting glucose and reduced insulin sensitivity in male Wistar rats.",
    quote:
      "Fasting glucose rose from 5.4 to 7.1 mmol/L (p = 0.008) under intermittent hypoxia; sustained hypoxia showed no significant change (p = 0.55).",
    subject: "fasting glucose homeostasis",
    organism: "rat (Wistar)",
    intervention: "intermittent vs sustained hypoxia, 6 weeks",
    dose: "FIO2 10% vs 10%",
    measurement: "fasting plasma glucose",
    effect_direction: "increase",
    effect_size: 0.32,
    p_value: 0.008,
    sample_size: 14,
    statistical_method: "repeated-measures ANOVA",
    confidence: "high",
  },
];

export const DEMO_CONFLICTS: Conflict[] = [
  {
    id: "x1",
    claim_a: "c1",
    claim_b: "c2",
    verdict: "contradiction",
    reasoning:
      "Both evaluate insulin/glucose handling under hypoxia in the same organism. Intermittent hypoxia decreases insulin-stimulated AKT phosphorylation, while sustained hypoxia improves glucose tolerance via AMPK — opposing directions on adjacent endpoint axes.",
    differences: [
      { factor: "exposure_regimen", a: "intermittent 8h/day", b: "sustained continuous" },
      { factor: "endpoint", a: "AKT phosphorylation", b: "GTT AUC" },
      { factor: "duration", a: "6 weeks", b: "4 weeks" },
    ],
  },
  {
    id: "x2",
    claim_a: "c1",
    claim_b: "c6",
    verdict: "conflict",
    reasoning:
      "Cross-species concordance on direction (intermittent hypoxia impairs glucose/insulin endpoints), but the rat study reports fasting glucose only; conflict is on measurability rather than direction.",
    differences: [
      { factor: "organism", a: "mouse C57BL/6J", b: "rat Wistar" },
      { factor: "endpoint", a: "pAKT Ser473", b: "fasting glucose" },
    ],
  },
  {
    id: "x3",
    claim_a: "c3",
    claim_b: "c1",
    verdict: "ambiguity",
    reasoning:
      "Benefit in hepatic insulin resistance without HIF-1α accumulation conflicts nominally with the muscle HIF-1α-mediated impairment; tissue-specific mechanisms cannot be adjudicated from these studies.",
    differences: [
      { factor: "tissue", a: "liver", b: "skeletal muscle" },
      { factor: "HIF-1α engagement", a: "not detected", b: "2.7-fold nuclear increase" },
    ],
  },
];

export const DEMO_MECHANISMS: MechanismChain[] = [
  {
    id: "m1",
    title: "Hypoxia → HIF-1α → metabolic interference",
    pathway: ["hypoxic exposure", "HIF-1α stabilization", "mTOR competition", "IRS-1 attenuation", "impaired insulin signaling"],
    evidence: ["c1", "c5"],
    hops: 4,
  },
  {
    id: "m2",
    title: "Sustained hypoxia → AMPK → GLUT4 translocation",
    pathway: ["sustained hypoxia", "AMP/ATP rise", "AMPK activation", "GLUT4 membrane translocation", "improved glucose uptake"],
    evidence: ["c2", "c4"],
    hops: 4,
  },
  {
    id: "m3",
    title: "Exposure regimen as the bifurcation variable",
    pathway: ["intermittent vs sustained profile", "differential ROS pulse", "HIF-1α vs AMPK bias", "divergent metabolic outcome"],
    evidence: ["c6", "c1", "c2"],
    hops: 3,
  },
];

export const DEMO_HYPOTHESES: Hypothesis[] = [
  {
    id: "h1",
    statement:
      "Intermittent hypoxia impairs skeletal muscle insulin signaling specifically via HIF-1α-driven mTOR sequestration, and pharmacological mTOR restraint will rescue AKT phosphorylation.",
    mechanism:
      "HIF-1α upregulates REDD1, releasing TSC1/2 inhibition of Rheb and diverting mTORC1 capacity away from IRS-1-associated translation complexes.",
    predictions: [
      "REDD1 knockdown restores pAKT under intermittent hypoxia",
      "Rapamycin co-treatment normalizes glucose infusion rate in hyperinsulinemic clamp",
    ],
    required_measurement: "pAKT Ser473 + REDD1 protein abundance",
    expected_result: "Rescue of pAKT to ≥80% of normoxic control under intermittent hypoxia + rapamycin",
    falsification_conditions: [
      "pAKT remains suppressed with rapamycin",
      "REDD1 ablation produces no change in insulin-stimulated phosphorylation",
    ],
    next_experiment: "Hyperinsulinemic-euglycemic clamp in REDD1 knockout vs wild-type under intermittent hypoxia",
    status: "proposed",
  },
  {
    id: "h2",
    statement:
      "The metabolic outcome of hypoxia is determined primarily by exposure temporal profile (intermittent vs sustained) rather than total hypoxic dose.",
    mechanism:
      "Intermittency generates periodic ROS bursts that bias signaling toward HIF-1α stabilization, while sustained mild hypoxia raises AMP/ATP and biases toward AMPK.",
    predictions: [
      "Matched total hypoxic time, different cycling periods, produce opposite insulin outcomes",
      "ROS scavenger (MitoTEMPO) abolishes the intermittent-hypoxia impairment",
    ],
    required_measurement: "GTT AUC + in vivo ROS (MitoB)",
    expected_result: "Crossover of outcomes when cycling period is varied at matched cumulative dose",
    falsification_conditions: [
      "Outcomes are indistinguishable at matched total dose",
      "MitoTEMPO has no effect on either profile",
    ],
    next_experiment: "Matched-dose design: 3h×2 cycles/day vs 6h×1 cycle/day vs sustained, 4 weeks",
    status: "proposed",
  },
];

export const DEMO_GAPS: ResearchGap[] = [
  { id: "g1", description: "No longitudinal kinetic data on durability of hypoxia-induced insulin sensitization after reoxygenation.", category: "temporal_gap" },
  { id: "g2", description: "Translational validity across organisms untested: rodent findings have no human matched-dose replication.", category: "translation_gap" },
  { id: "g3", description: "Sex as a biological variable is unreported in 4 of 6 studies.", category: "reporting_gap" },
];

export const DEMO_GEO: GeoClosure[] = [
  {
    id: "geo1",
    gse_accession: "GSE132054",
    title: "Intermittent hypoxia transcriptional response in murine skeletal muscle (Gene Expression Omnibus)",
    organism: "Mus musculus",
    n_samples: 12,
    links_claims: ["c1", "c6"],
    resolution:
      "Series contains matched normoxic/intermittent-hypoxic gastrocnemius microarrays; REDD1 and downstream mTOR targets are testable against h1 predictions.",
  },
];

export const DEMO_AUDIT: AuditFlag[] = [
  { id: "a1", severity: "warn", target: "x2", message: "Cross-species comparison flagged: rodent strain and endpoint differ; direction concordance only." },
  { id: "a2", severity: "critical", target: "c2", message: "Effect direction recorded as 'increase' for GTT AUC while the abstract reports an AUC reduction; polarity corrected during audit." },
  { id: "a3", severity: "info", target: "g3", message: "Multiple studies omit sex-disaggregated reporting; treated as a research gap rather than exclusion." },
];

export const DEMO_LOG_SCRIPT: Array<{ stage: StageKey; delay: number; lines: Array<{ level: LogEvent["level"]; message: string }> }> = [
  {
    stage: "retrieval",
    delay: 420,
    lines: [
      { level: "info", message: "query building: synonyms + MeSH expansion → 4 query variants" },
      { level: "info", message: "europe_pmc: 38 hits → relevance filter 0.30 → 6 retained" },
      { level: "info", message: "pubmed: 12 hits, 2 new after DOI dedup" },
      { level: "info", message: "crossref: metadata backfill for 2 items" },
    ],
  },
  {
    stage: "extraction",
    delay: 520,
    lines: [
      { level: "info", message: "parsing full text XML (JATS) for 3 open-access items" },
      { level: "info", message: "claim extraction: 6 claims, 6/6 anchored to verbatim quotes" },
      { level: "info", message: "statistical layer: effect_direction + p-value parsed for 6/6" },
    ],
  },
  {
    stage: "contradictions",
    delay: 460,
    lines: [
      { level: "info", message: "clustering claims by subject axis → 4 groups" },
      { level: "info", message: "pairwise comparison: 1 contradiction, 1 conflict, 1 ambiguity" },
    ],
  },
  {
    stage: "geo",
    delay: 520,
    lines: [
      { level: "info", message: "GEO search for conflict targets: GSE132054 matched" },
      { level: "info", message: "loop closure: 1 empirical series linked to 2 claims" },
    ],
  },
  {
    stage: "pathways",
    delay: 480,
    lines: [
      { level: "info", message: "entity graph: 24 nodes, 31 relations" },
      { level: "info", message: "multi-hop chains: 3 pathways (3–4 hops)" },
    ],
  },
  {
    stage: "hypotheses",
    delay: 540,
    lines: [
      { level: "info", message: "formulating falsifiable hypotheses → 2" },
      { level: "info", message: "research gaps identified → 3" },
    ],
  },
  {
    stage: "audit",
    delay: 470,
    lines: [
      { level: "flag", message: "audit: polarity correction applied to c2" },
      { level: "flag", message: "audit: cross-species comparison flagged (x2)" },
    ],
  },
  {
    stage: "report",
    delay: 380,
    lines: [{ level: "info", message: "assembling dossier + markdown report" }],
  },
];

export function demoInvestigation(question: string, startedAt: number): Investigation {
  const papers = [...DEMO_PAPERS];
  const claims = [...DEMO_CLAIMS];
  return {
    id: `demo_${Math.random().toString(36).slice(2, 8)}`,
    question,
    mode: "pipeline",
    created_at: startedAt,
    duration_ms: Date.now() - startedAt,
    demo: true,
    summary: {
      papers_analyzed: papers.length,
      claims: claims.length,
      evidence_anchors: claims.length,
      conflict_groups: 3,
      conflicting_pairs: 3,
      hypotheses: 2,
      research_gaps: 3,
      audit_flags: 3,
      geo_closures: 1,
    },
    papers,
    claims,
    conflicts: [...DEMO_CONFLICTS],
    mechanisms: [...DEMO_MECHANISMS],
    hypotheses: [...DEMO_HYPOTHESES],
    gaps: [...DEMO_GAPS],
    geo_closures: [...DEMO_GEO],
    audit_flags: [...DEMO_AUDIT],
  };
}
