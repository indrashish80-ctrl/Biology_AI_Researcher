import type { Health, JobEvent } from "./types";
import { DEMO_LOG_SCRIPT, demoInvestigation } from "./demo";

/**
 * Live-frontend contract with the FastAPI layer (api/server.py):
 *   GET  /api/health            -> { ok, providers: string[], ready, version }
 *   POST /api/investigate       -> { job_id }
 *   GET  /api/jobs/:id/events   -> SSE with NAMED events:
 *                                    event: log   data: { text }
 *                                    event: stage data: { status, stage, progress, message }
 *                                    event: done  data: { status, stage, progress, message }
 *                                    event: error data: { error }
 *   GET  /api/jobs/:id/result   -> { question, answer, report (markdown), dossier }
 *   POST /api/dataset           -> upload experimental CSV/XLSX
 *
 * When the backend is unreachable (static deploy / no Python engine),
 * startInvestigation falls back to a deterministic demo replay.
 */

const BASE = "";

export async function fetchHealth(): Promise<Health | null> {
  try {
    const r = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(2500) });
    if (!r.ok) return null;
    const d = (await r.json()) as { ok?: boolean; providers?: string[]; ready?: boolean };
    if (typeof d?.ok !== "boolean") return null;
    return { engine: "fastapi", providers: Object.fromEntries((d.providers ?? []).map((p) => [p, true])), demo_mode: !d.ready };
  } catch {
    return null;
  }
}

/** Handler returns false to close the stream (prevents EventSource auto-reconnect replay loops). */
type NamedSseHandler = (event: string, data: string) => boolean | void;

function openNamedStream(url: string, handler: NamedSseHandler): () => void {
  const es = new EventSource(url);
  const forward = (name: string) => (ev: MessageEvent) => {
    if (handler(name, ev.data) === false) es.close();
  };
  const log = forward("log");
  const stage = forward("stage");
  const done = forward("done");
  const error = forward("error");
  es.addEventListener("log", log as EventListener);
  es.addEventListener("stage", stage as EventListener);
  es.addEventListener("done", done as EventListener);
  es.addEventListener("error", error as EventListener);
  es.onmessage = (m) => handler("message", m.data);
  return () => es.close();
}

export function startInvestigation(
  question: string,
  mode: "pipeline" | "agent",
  onEvent: (e: JobEvent) => void,
): () => void {
  let cancelled = false;
  let cancelLive: (() => void) | null = null;
  let fallbackAllowed = true;

  onEvent({ type: "log", level: "info", message: "contacting research engine…" });

  fetch(`${BASE}/api/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode }),
    signal: AbortSignal.timeout(4000),
  })
    .then(async (r) => {
      if (cancelled) return;
      // Explicit refusals (no key configured, bad question) surface as errors —
      // they must NOT silently fall back to the demo replay.
      if (r.status === 403 || r.status === 400) {
        fallbackAllowed = false;
        const d = (await r.json().catch(() => null)) as { detail?: string } | null;
        onEvent({ type: "error", message: d?.detail ?? `Engine refused the job (HTTP ${r.status}).` });
        return;
      }
      if (r.ok) {
        const data = (await r.json()) as { job_id?: string };
        if (data?.job_id) {
          const jobId = data.job_id;
          let closeStream = false;
          cancelLive = openNamedStream(`${BASE}/api/jobs/${jobId}/events`, (name, raw) => {
            if (cancelled) return;
            let d: Record<string, unknown> = {};
            try {
              d = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
            } catch {
              return;
            }
            if (name === "log") {
              onEvent({ type: "log", level: "info", message: String(d.text ?? "") });
            } else if (name === "stage") {
              onEvent({
                type: "stage",
                stage: String(d.stage ?? ""),
                message: String(d.message ?? ""),
                progress: typeof d.progress === "number" ? d.progress : undefined,
              });
            } else if (name === "done") {
              onEvent({ type: "log", level: "info", message: "run complete — fetching dossier…" });
              // Terminal event: stop the stream so EventSource cannot
              // auto-reconnect and replay the whole job from the start.
              closeStream = true;
              fetch(`${BASE}/api/jobs/${jobId}/result`)
                .then((res) => (res.ok ? res.json() : Promise.reject(new Error(String(res.status)))))
                .then((result: { question?: string; answer?: string; report?: string; dossier?: unknown }) => {
                  if (cancelled) return;
                  onEvent({
                    type: "done",
                    investigation: normalizeResult(question, mode, result, jobId),
                  });
                })
                .catch(() => {
                  if (!cancelled) onEvent({ type: "error", message: "Could not fetch the investigation result." });
                });
            } else if (name === "error") {
              closeStream = true;
              onEvent({ type: "error", message: String(d.error ?? "Engine reported an error.") });
            }
            if (closeStream) return false;
          });
          return;
        }
      }
      if (!cancelled && !cancelLive && fallbackAllowed) {
        onEvent({ type: "log", level: "warn", message: "engine unavailable — running deterministic demo replay" });
        cancelLive = replayDemo(question, mode, onEvent);
      }
    })
    .catch(() => {
      if (!cancelled && !cancelLive && fallbackAllowed) {
        onEvent({ type: "log", level: "warn", message: "engine unreachable — running deterministic demo replay" });
        cancelLive = replayDemo(question, mode, onEvent);
      }
    });

  return () => {
    cancelled = true;
    cancelLive?.();
  };
}

/** Map the engine's result payload onto the UI's Investigation model. */
function normalizeResult(
  question: string,
  mode: "pipeline" | "agent",
  result: { question?: string; answer?: string; report?: string; dossier?: unknown },
  jobId: string,
): InvestigationAlias {
  const dossier = (result.dossier ?? {}) as Record<string, unknown>;
  const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
  const papers = arr(dossier.papers ?? dossier.sources);
  const claims = arr(dossier.claims);
  const contradictions = arr(dossier.contradictions ?? dossier.conflicts);
  const chains = arr(dossier.pathway_chains ?? dossier.mechanisms);
  const hypotheses = arr(dossier.hypotheses);
  const gaps = arr(dossier.research_gaps ?? dossier.gaps);
  const geo = arr(dossier.empirical_geo_closures ?? dossier.geo_closures);
  const audit = arr(dossier.audit_flags);
  const summary = (dossier.evidence_summary ?? {}) as Record<string, unknown>;
  const num = (v: unknown, fallback: number): number => (typeof v === "number" ? v : fallback);

  return {
    id: jobId,
    question: result.question ?? question,
    mode,
    created_at: Date.now(),
    duration_ms: 0,
    demo: false,
    summary: {
      papers_analyzed: num(summary.papers, num(dossier.papers_analyzed, papers.length)),
      claims: num(summary.claims, claims.length),
      evidence_anchors: num(summary.evidence, claims.length),
      conflict_groups: num(summary.conflict_groups, contradictions.length),
      conflicting_pairs: num(summary.conflicting_pairs, contradictions.length),
      hypotheses: hypotheses.length,
      research_gaps: gaps.length,
      audit_flags: audit.length,
      geo_closures: geo.length,
    },
    papers: papers as InvestigationAlias["papers"],
    claims: claims as InvestigationAlias["claims"],
    conflicts: contradictions as InvestigationAlias["conflicts"],
    mechanisms: chains as InvestigationAlias["mechanisms"],
    hypotheses: hypotheses as InvestigationAlias["hypotheses"],
    gaps: gaps as InvestigationAlias["gaps"],
    geo_closures: geo as InvestigationAlias["geo_closures"],
    audit_flags: audit as InvestigationAlias["audit_flags"],
    report_md: result.report ?? "",
    answer: result.answer ?? "",
    raw_dossier: dossier,
  };
}

type InvestigationAlias = import("./types").Investigation;

function replayDemo(
  question: string,
  mode: "pipeline" | "agent",
  onEvent: (e: JobEvent) => void,
): () => void {
  const startedAt = Date.now();
  const timers: number[] = [];
  let t = 350;
  for (const beat of DEMO_LOG_SCRIPT) {
    const beatStart = t;
    timers.push(
      window.setTimeout(
        () => onEvent({ type: "stage", stage: beat.stage, message: stageVerb(beat.stage) }),
        beatStart,
      ),
    );
    for (const line of beat.lines) {
      t += beat.delay;
      timers.push(window.setTimeout(() => onEvent({ type: "log", level: line.level, message: line.message }), t));
    }
    t += 160;
  }
  timers.push(
    window.setTimeout(
      () => onEvent({ type: "done", investigation: demoInvestigation(question, startedAt) }),
      t + 300,
    ),
  );
  void mode;
  return () => timers.forEach((id) => window.clearTimeout(id));
}

function stageVerb(stage: string): string {
  const map: Record<string, string> = {
    retrieval: "Acquiring literature from open databases",
    extraction: "Extracting quote-grounded claims",
    contradictions: "Detecting cross-study contradictions",
    geo: "Closing the loop with GEO datasets",
    pathways: "Synthesizing mechanistic pathways",
    hypotheses: "Formulating falsifiable hypotheses",
    audit: "Running adversarial audit",
    report: "Assembling research dossier",
    startup: "Starting the research engine",
    engine: "Engine initializing",
    agent: "Autonomous agent running",
    complete: "Investigation complete",
    error: "Engine error",
  };
  return map[stage] ?? (stage ? stage.replace(/_/g, " ") : "working");
}

export interface KeyStatus {
  groq: boolean;
  nvidia: boolean;
  gemini: boolean;
  ready: boolean;
}

export async function fetchKeyStatus(): Promise<KeyStatus | null> {
  try {
    const r = await fetch(`${BASE}/api/keys`, { signal: AbortSignal.timeout(2500) });
    if (!r.ok) return null;
    const d = (await r.json()) as Partial<KeyStatus>;
    if (typeof d.ready !== "boolean") return null;
    return { groq: !!d.groq, nvidia: !!d.nvidia, gemini: !!d.gemini, ready: d.ready };
  } catch {
    return null;
  }
}

export async function saveKeys(keys: {
  groq_key?: string;
  nvidia_key?: string;
  gemini_key?: string;
}): Promise<KeyStatus | null> {
  try {
    const r = await fetch(`${BASE}/api/keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(keys),
    });
    if (!r.ok) return null;
    const d = (await r.json()) as Partial<KeyStatus>;
    return { groq: !!d.groq, nvidia: !!d.nvidia, gemini: !!d.gemini, ready: !!d.ready };
  } catch {
    return null;
  }
}

export async function clearKeys(): Promise<KeyStatus | null> {
  try {
    const r = await fetch(`${BASE}/api/keys`, { method: "DELETE" });
    if (!r.ok) return null;
    const d = (await r.json()) as Partial<KeyStatus>;
    return { groq: !!d.groq, nvidia: !!d.nvidia, gemini: !!d.gemini, ready: !!d.ready };
  } catch {
    return null;
  }
}

export async function uploadDataset(
  file: File,
): Promise<{ ok: boolean; statement?: string; error?: string }> {
  try {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`${BASE}/api/dataset`, { method: "POST", body: fd });
    if (!r.ok) return { ok: false, error: `Server responded ${r.status}` };
    const data = (await r.json()) as { statement?: string };
    return { ok: true, statement: data.statement };
  } catch {
    return { ok: false, error: "Backend unreachable — dataset bridge requires the Python engine." };
  }
}
