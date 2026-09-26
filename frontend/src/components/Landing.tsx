import { useEffect, useState } from "react";
import { Badge, HelixMark, Panel, SectionTitle, Spark } from "./ui";
import { cn } from "../lib/utils";

const CAPABILITIES = [
  {
    tag: "01",
    title: "Multi-source literature retrieval",
    body: "Queries PubMed, Europe PMC, PMC Open Access and Crossref in parallel; hierarchical DOI → PMID → PMCID → title dedup keeps the corpus clean.",
    glyph: "⌗",
  },
  {
    tag: "02",
    title: "Quote-grounded claim extraction",
    body: "Every claim is anchored to a verbatim quote from the source paper — no floating summaries. Effect direction, size, p-value and n parsed deterministically.",
    glyph: "❝",
  },
  {
    tag: "03",
    title: "Contradiction detection",
    body: "Cross-study directional analysis finds where independent studies disagree, separates true contradictions from ambiguities, and shows the material differences.",
    glyph: "≠",
  },
  {
    tag: "04",
    title: "Mechanistic pathway synthesis",
    body: "Multi-hop mechanism chains assembled across studies — from exposure profile to molecular signaling to whole-body outcome.",
    glyph: "⑃",
  },
  {
    tag: "05",
    title: "Falsifiable hypotheses",
    body: "Hypotheses come with required measurements, expected results, explicit falsification conditions and a designed next experiment.",
    glyph: "⧉",
  },
  {
    tag: "06",
    title: "Adversarial critic",
    body: "A deterministic red-team pass audits every synthesized claim — polarity corrections, cross-species flags, reporting gaps — before the dossier ships.",
    glyph: "⚑",
  },
];

const PIPELINE = [
  { key: "retrieval", label: "Acquire", detail: "PubMed · Europe PMC · Crossref" },
  { key: "extraction", label: "Extract", detail: "quote-anchored claims" },
  { key: "contradictions", label: "Contradict", detail: "cross-study deltas" },
  { key: "geo", label: "Close loop", detail: "NCBI GEO datasets" },
  { key: "pathways", label: "Synthesize", detail: "multi-hop mechanisms" },
  { key: "hypotheses", label: "Hypothesize", detail: "falsifiable designs" },
  { key: "audit", label: "Red-team", detail: "adversarial audit" },
  { key: "report", label: "Dossier", detail: "report + evidence JSON" },
];

const API_ROWS = [
  { m: "GET", p: "/api/health", d: "provider status + demo mode" },
  { m: "POST", p: "/api/dataset", d: "upload experimental CSV / XLSX" },
  { m: "POST", p: "/api/investigate", d: "start a job — mode: pipeline | agent" },
  { m: "GET", p: "/api/jobs/:id", d: "job snapshot (stage, progress)" },
  { m: "GET", p: "/api/jobs/:id/events", d: "SSE live progress stream" },
  { m: "GET", p: "/api/jobs/:id/result", d: "report + dossier JSON" },
];

function useTypedLine(lines: string[], speed = 34, hold = 2000) {
  const [idx, setIdx] = useState(0);
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<"typing" | "hold">("typing");

  useEffect(() => {
    let t: number;
    const line = lines[idx % lines.length];
    if (phase === "typing") {
      if (text.length < line.length) {
        t = window.setTimeout(() => setText(line.slice(0, text.length + 1)), speed);
      } else {
        t = window.setTimeout(() => setPhase("hold"), 350);
      }
    } else {
      t = window.setTimeout(() => {
        setText("");
        setPhase("typing");
        setIdx((i) => (i + 1) % lines.length);
      }, hold);
    }
    return () => window.clearTimeout(t);
  }, [text, phase, idx, lines, speed, hold]);

  return text;
}

export function Landing({
  enterConsole,
  openKeys,
}: {
  enterConsole: () => void;
  openKeys?: () => void;
}) {
  const typed = useTypedLine([
    "Does hypoxia impair insulin signaling via HIF-1α?",
    "Which studies contradict each other, and why?",
    "What experiment would falsify this mechanism?",
    "Close the loop against real GEO datasets.",
  ]);

  return (
    <main className="relative">
      {/* ── hero ─────────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-36 pb-24 sm:pt-44">
        <div className="bg-grid absolute inset-0" aria-hidden />
        <div
          className="absolute -top-40 left-1/2 h-[560px] w-[860px] -translate-x-1/2 rounded-full bg-mint/10 blur-[140px] animate-drift"
          aria-hidden
        />
        <div
          className="absolute top-40 right-[8%] h-72 w-72 rounded-full bg-bio/10 blur-[110px] animate-drift"
          aria-hidden
        />
        <div className="bg-noise pointer-events-none absolute inset-0 opacity-60" aria-hidden />

        <div className="relative mx-auto max-w-6xl px-5">
          <div className="animate-rise">
            <Badge className="border-mint/30 bg-mint/8 text-mint">
              <Spark /> autonomous research engine
            </Badge>
          </div>

          <h1 className="animate-rise mt-7 max-w-4xl font-display text-5xl leading-[1.04] text-white sm:text-7xl [animation-delay:80ms]">
            The biology research engine that{" "}
            <em className="text-glow not-italic text-mint">shows its evidence.</em>
          </h1>

          <p className="animate-rise mt-7 max-w-2xl text-lg leading-relaxed text-mist [animation-delay:160ms]">
            BioSynthetica reads the literature like a painstaking postdoc: retrieves papers across four
            databases, extracts claims anchored to verbatim quotes, hunts down contradictions between
            studies, closes the loop with real datasets — then lets an adversarial critic tear into its
            own conclusions.
          </p>

          <div className="animate-rise mt-10 flex flex-wrap items-center gap-4 [animation-delay:240ms]">
            <button
              onClick={enterConsole}
              className="group relative overflow-hidden rounded-full bg-mint px-7 py-3.5 font-mono text-sm font-semibold text-void transition-all hover:shadow-[0_0_40px_-8px_rgba(61,255,178,0.7)]"
            >
              <span className="relative z-10">Run an investigation →</span>
              <span className="absolute inset-0 mint-flow opacity-0 transition-opacity group-hover:opacity-20" />
            </button>
            <a
              href="#pipeline"
              className="rounded-full border border-edge-hi px-7 py-3.5 font-mono text-sm text-ghost transition hover:border-mint/40 hover:text-white"
            >
              see the pipeline
            </a>
          </div>

          {/* terminal */}
          <Panel className="animate-rise relative mt-16 overflow-hidden [animation-delay:320ms]" glow>
            <div className="flex items-center gap-2 border-b border-edge/60 px-4 py-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-bio/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-bio/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-mint/60" />
              <span className="ml-3 font-mono text-[11px] text-mist">biosynthetica — investigation console</span>
            </div>
            <div className="relative px-5 py-6 font-mono text-sm leading-7">
              <div className="text-mist">
                <span className="text-mint">$</span> investigate{" "}
                <span className="text-ghost">"{typed}</span>
                <span className="animate-blink text-mint">▌</span>
              </div>
              <div className="absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-mint/5 to-transparent [animation:scan_2.8s_ease-in-out_infinite] overflow-hidden pointer-events-none" />
              <div className="mt-3 grid grid-cols-2 gap-x-8 gap-y-1 text-[12px] text-mist sm:grid-cols-4">
                <div>retrieval <span className="text-mint">✓</span></div>
                <div>claims <span className="text-mint">✓</span></div>
                <div>contradictions <span className="text-mint">✓</span></div>
                <div>geo closure <span className="text-mint">✓</span></div>
              </div>
            </div>
          </Panel>

          {/* stat strip */}
          <div className="mt-14 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["4", "literature sources"],
              ["100%", "claims quote-anchored"],
              ["8", "pipeline stages"],
              ["0", "unaudited conclusions"],
            ].map(([v, l], i) => (
              <div
                key={l}
                className={cn(
                  "hairline rounded-xl bg-carbon/50 px-5 py-4 animate-rise",
                  i === 0 && "text-left",
                )}
                style={{ animationDelay: `${360 + i * 70}ms` }}
              >
                <div className="font-mono text-2xl font-semibold text-mint">{v}</div>
                <div className="mt-1 text-[11px] uppercase tracking-[0.16em] text-mist">{l}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── capabilities ─────────────────────────────────────── */}
      <section id="capabilities" className="relative mx-auto max-w-6xl scroll-mt-24 px-5 py-24">
        <SectionTitle
          kicker="capabilities"
          title={
            <>
              Deterministic where it matters.
              <br />
              <span className="text-mist">Generative where it helps.</span>
            </>
          }
        />
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((c) => (
            <Panel
              key={c.tag}
              className="group relative overflow-hidden p-6 transition-all duration-300 hover:-translate-y-1 hover:border-mint/35 hover:shadow-[0_18px_50px_-24px_rgba(61,255,178,0.35)]"
            >
              <div className="flex items-start justify-between">
                <span className="text-2xl text-mint/90">{c.glyph}</span>
                <span className="font-mono text-[11px] text-mist/60">{c.tag}</span>
              </div>
              <h3 className="mt-5 text-[15px] font-semibold text-white">{c.title}</h3>
              <p className="mt-2.5 text-[13px] leading-relaxed text-mist">{c.body}</p>
              <span className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-mint/50 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
            </Panel>
          ))}
        </div>
      </section>

      {/* ── pipeline ─────────────────────────────────────────── */}
      <section id="pipeline" className="relative scroll-mt-24 border-y border-edge/50 bg-ink/60 py-24 stripe-soft">
        <div className="mx-auto max-w-6xl px-5">
          <SectionTitle
            kicker="the closed loop"
            title="Eight stages, one dossier"
            right={
              <div className="hidden text-right font-mono text-[11px] leading-5 text-mist md:block">
                deterministic checks at every hop
                <br />
                <span className="text-mint">✓ provenance · ✓ polarity · ✓ power</span>
              </div>
            }
          />
          <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-edge/60 bg-edge/40 sm:grid-cols-2 lg:grid-cols-4">
            {PIPELINE.map((s, i) => (
              <div key={s.key} className="group relative bg-ink/90 p-6 transition-colors hover:bg-carbon">
                <div className="font-mono text-[11px] text-mint/80">{String(i + 1).padStart(2, "0")}</div>
                <div className="mt-3 font-display text-xl text-white">{s.label}</div>
                <div className="mt-1 font-mono text-[11px] text-mist">{s.detail}</div>
                <span className="absolute right-4 top-5 text-edge-hi transition-colors group-hover:text-mint/60">
                  →
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── evidence ─────────────────────────────────────────── */}
      <section id="evidence" className="relative mx-auto max-w-6xl scroll-mt-24 px-5 py-24">
        <SectionTitle
          kicker="why quote-grounded"
          title={
            <>
              Claims you can <span className="text-mint">grep back</span> to the paper.
            </>
          }
        />
        <div className="mt-12 grid gap-5 lg:grid-cols-5">
          <Panel className="p-6 lg:col-span-3">
            <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-mist">extracted claim</div>
            <div className="mt-4 rounded-xl border border-edge/70 bg-void/70 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="border-bio/30 bg-bio/8 text-bio">↓ decrease</Badge>
                <Badge className="border-edge-hi text-mist">p = 0.011</Badge>
                <Badge className="border-edge-hi text-mist">n = 12</Badge>
                <Badge className="border-mint/30 bg-mint/8 text-mint">confidence: high</Badge>
              </div>
              <p className="mt-4 text-[14px] leading-relaxed text-ghost">
                Intermittent hypoxia stabilized HIF-1α and impaired insulin-stimulated AKT
                phosphorylation in murine skeletal muscle.
              </p>
              <blockquote className="mt-4 border-l-2 border-mint/50 pl-4 font-mono text-[12px] leading-relaxed text-mist">
                "…significantly increased nuclear HIF-1α (2.7-fold, p = 0.004) and reduced
                insulin-stimulated AKT Ser473 phosphorylation by 38% relative to normoxic controls
                (p = 0.011)."
              </blockquote>
              <div className="mt-4 font-mono text-[11px] text-mint/80">
                ↳ J Appl Physiol · 2021 · doi:10.1152/japplphysiol.00123.2021
              </div>
            </div>
          </Panel>
          <div className="flex flex-col gap-5 lg:col-span-2">
            <Panel className="flex-1 p-6">
              <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-mist">contradiction radar</div>
              <div className="mt-4 space-y-3">
                {[
                  ["c1 ↔ c2", "contradiction", "text-rose-bio border-rose-bio/40"],
                  ["c1 ↔ c6", "conflict", "text-amber-bio border-amber-bio/30"],
                  ["c3 ↔ c1", "ambiguity", "text-violet-bio border-violet-bio/30"],
                ].map(([pair, verdict, cls]) => (
                  <div key={pair} className="flex items-center justify-between rounded-lg border border-edge/60 bg-void/60 px-3.5 py-2.5">
                    <span className="font-mono text-[12px] text-ghost">{pair}</span>
                    <span className={cn("rounded-full border px-2 py-0.5 font-mono text-[10px]", cls)}>{verdict}</span>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-[13px] leading-relaxed text-mist">
                Exposure regimen — intermittent vs sustained — emerges as the bifurcation variable.
              </p>
            </Panel>
            <Panel className="p-6">
              <div className="flex items-center gap-3">
                <HelixMark className="h-9 w-9" />
                <div>
                  <div className="text-[13px] font-semibold text-white">GEO loop closure</div>
                  <div className="font-mono text-[11px] text-mist">
                    conflicts → <span className="text-mint">GSE132054</span> · n=12 · testable
                  </div>
                </div>
              </div>
            </Panel>
          </div>
        </div>
      </section>

      {/* ── api ──────────────────────────────────────────────── */}
      <section id="api" className="relative scroll-mt-24 border-t border-edge/50 bg-ink/60 py-24">
        <div className="mx-auto max-w-6xl px-5">
          <SectionTitle
            kicker="bring your own engine"
            title="The console speaks your API"
            right={
              openKeys && (
                <button
                  onClick={openKeys}
                  className="rounded-full border border-mint/40 bg-mint/10 px-4 py-2 font-mono text-[12px] text-mint transition hover:bg-mint/20"
                >
                  🔑 set your LLM keys
                </button>
              )
            }
          />
          <div className="mt-12 grid gap-5 lg:grid-cols-2">
            <Panel className="overflow-hidden">
              <div className="border-b border-edge/60 px-5 py-3 font-mono text-[11px] text-mist">REST + SSE contract</div>
              <div className="divide-y divide-edge/40">
                {API_ROWS.map((r) => (
                  <div key={r.p} className="flex items-center gap-4 px-5 py-3 transition hover:bg-carbon/60">
                    <span
                      className={cn(
                        "w-11 shrink-0 rounded border px-1.5 py-0.5 text-center font-mono text-[10px]",
                        r.m === "GET" ? "border-bio/30 text-bio" : "border-mint/30 text-mint",
                      )}
                    >
                      {r.m}
                    </span>
                    <span className="font-mono text-[13px] text-ghost">{r.p}</span>
                    <span className="ml-auto hidden text-[11px] text-mist sm:block">{r.d}</span>
                  </div>
                ))}
              </div>
            </Panel>
            <Panel className="overflow-hidden">
              <div className="border-b border-edge/60 px-5 py-3 font-mono text-[11px] text-mist">
                run it locally — FastAPI serves this UI
              </div>
              <pre className="overflow-x-auto p-5 font-mono text-[12.5px] leading-7 text-ghost">
{`# install python engine + frontend deps
bun run setup

# start the server, then add your LLM key inside the app (🔑 keys)
bun run dev

# or run the engine directly
python research_engine.py "your question" --max-papers 6`}
              </pre>
            </Panel>
          </div>
        </div>
      </section>

      {/* ── final CTA ────────────────────────────────────────── */}
      <section className="relative overflow-hidden py-28">
        <div
          className="absolute bottom-0 left-1/2 h-[420px] w-[760px] -translate-x-1/2 rounded-full bg-mint/8 blur-[130px]"
          aria-hidden
        />
        <div className="relative mx-auto max-w-3xl px-5 text-center">
          <HelixMark className="mx-auto h-14 w-14" />
          <h2 className="mt-8 font-display text-4xl text-white sm:text-5xl">
            Ask biology a real question.
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-mist">
            Add your own LLM key, ask a real question — retrieval, contradiction hunting and
            adversarial review run on your key, never ours.
          </p>
          <button
            onClick={enterConsole}
            className="mt-9 rounded-full bg-mint px-8 py-4 font-mono text-sm font-semibold text-void transition-all hover:shadow-[0_0_44px_-8px_rgba(61,255,178,0.7)]"
          >
            Open the console →
          </button>
        </div>
      </section>

      <footer className="border-t border-edge/50 py-10">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 font-mono text-[11px] text-mist">
          <div className="flex items-center gap-2">
            <HelixMark className="h-4 w-4" />
            <span>BioSynthetica — autonomous biology research engine</span>
          </div>
          <div>engine: Python · FastAPI · SQLite — console: React · Vite · Tailwind</div>
        </div>
      </footer>
    </main>
  );
}
