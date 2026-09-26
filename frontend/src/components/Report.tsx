import { useState, type ReactNode } from "react";
import type { Claim, Investigation } from "../lib/types";
import { DIRECTION_META, SEVERITY_META, VERDICT_META, cn, downloadJson, downloadText, fmtEffect, fmtP } from "../lib/utils";
import { dossierToMarkdown } from "../lib/report";
import { Badge, Panel, Stat } from "./ui";

type Tab = "report" | "claims" | "conflicts" | "mechanisms" | "hypotheses" | "gaps" | "geo" | "audit" | "sources";

const TABS: Array<{ key: Tab; label: string; count: (inv: Investigation) => number }> = [
  { key: "report", label: "Report", count: () => 0 },
  { key: "claims", label: "Claims", count: (i) => i.claims.length },
  { key: "conflicts", label: "Conflicts", count: (i) => i.conflicts.length },
  { key: "mechanisms", label: "Mechanisms", count: (i) => i.mechanisms.length },
  { key: "hypotheses", label: "Hypotheses", count: (i) => i.hypotheses.length },
  { key: "gaps", label: "Gaps", count: (i) => i.gaps.length },
  { key: "geo", label: "GEO", count: (i) => i.geo_closures.length },
  { key: "audit", label: "Audit", count: (i) => i.audit_flags.length },
  { key: "sources", label: "Sources", count: (i) => i.papers.length },
];

export function Report({ inv }: { inv: Investigation }) {
  const [tab, setTab] = useState<Tab>("report");

  return (
    <div className="animate-rise space-y-6">
      {/* header */}
      <Panel className="p-6" glow>
        <div className="flex flex-wrap items-center gap-3">
          <Badge className="border-mint/30 bg-mint/8 text-mint">
            {inv.demo ? "demo replay" : "live engine"} · {inv.mode}
          </Badge>
          <Badge className="border-edge-hi text-mist">{(inv.duration_ms / 1000).toFixed(1)}s</Badge>
          <Badge className="border-edge-hi text-mist">{inv.id}</Badge>
          <div className="ml-auto flex gap-2">
            <button
              onClick={() => downloadJson(`dossier_${inv.id}.json`, inv)}
              className="rounded-lg border border-edge-hi px-3 py-1.5 font-mono text-[11px] text-ghost transition hover:border-mint/40 hover:text-mint"
            >
              ↓ dossier.json
            </button>
            <button
              onClick={() => downloadText(`report_${inv.id}.md`, dossierToMarkdown(inv))}
              className="rounded-lg border border-edge-hi px-3 py-1.5 font-mono text-[11px] text-ghost transition hover:border-mint/40 hover:text-mint"
            >
              ↓ report.md
            </button>
          </div>
        </div>
        <h2 className="mt-4 font-display text-2xl leading-snug text-white">{inv.question}</h2>
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
          <Stat value={inv.summary.papers_analyzed} label="papers" />
          <Stat value={inv.summary.claims} label="claims" />
          <Stat value={inv.summary.conflicting_pairs} label="conflicts" accent="text-rose-bio" />
          <Stat value={inv.mechanisms.length} label="mechanisms" accent="text-bio" />
          <Stat value={inv.summary.hypotheses} label="hypotheses" accent="text-violet-bio" />
          <Stat value={inv.summary.geo_closures} label="geo links" accent="text-amber-bio" />
          <Stat value={inv.summary.audit_flags} label="audit flags" accent="text-amber-bio" />
        </div>
      </Panel>

      {/* tabs */}
      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => {
          const n = t.count(inv);
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={cn(
                "rounded-full border px-4 py-1.5 font-mono text-[12px] transition-all",
                tab === t.key
                  ? "border-mint/50 bg-mint/12 text-mint"
                  : "border-edge-hi text-mist hover:border-mint/30 hover:text-ghost",
              )}
            >
              {t.label} {t.key !== "report" && <span className="opacity-60">{n}</span>}
            </button>
          );
        })}
      </div>

      {tab === "report" && <ReportView inv={inv} />}
      {tab === "claims" && <ClaimsView claims={inv.claims} inv={inv} />}
      {tab === "conflicts" && <ConflictsView inv={inv} />}
      {tab === "mechanisms" && <MechanismsView inv={inv} />}
      {tab === "hypotheses" && <HypothesesView inv={inv} />}
      {tab === "gaps" && <GapsView inv={inv} />}
      {tab === "geo" && <GeoView inv={inv} />}
      {tab === "audit" && <AuditView inv={inv} />}
      {tab === "sources" && <SourcesView inv={inv} />}
    </div>
  );
}

function paperMeta(inv: Investigation, paperId: string) {
  const p = inv.papers.find((x) => x.id === paperId);
  return p && typeof p === "object" && "journal" in p ? `${p.journal} · ${p.year}` : String(paperId);
}

/** Lightweight markdown-ish renderer for the engine's report (headings, bullets, bold, quotes). */
function ReportView({ inv }: { inv: Investigation }) {
  const text = inv.report_md || inv.answer || "";
  if (!text.trim()) {
    return <Empty text="The engine returned no narrative report — inspect the structured tabs instead." />;
  }
  const lines = text.split("\n");
  return (
    <Panel className="p-6 sm:p-8">
      <div className="space-y-1.5">
        {lines.map((line, i) => {
          const t = line.trim();
          if (!t) return <div key={i} className="h-2" />;
          if (t.startsWith("# "))
            return (
              <h1 key={i} className="font-display text-2xl text-white pt-2">{inline(t.slice(2))}</h1>
            );
          if (t.startsWith("## "))
            return (
              <h2 key={i} className="mt-5 border-b border-edge/60 pb-2 font-mono text-[12px] uppercase tracking-[0.2em] text-mint">{inline(t.slice(3))}</h2>
            );
          if (t.startsWith("### "))
            return (
              <h3 key={i} className="mt-4 text-[15px] font-semibold text-white">{inline(t.slice(4))}</h3>
            );
          if (t.startsWith("> "))
            return (
              <blockquote key={i} className="border-l-2 border-mint/40 pl-4 font-mono text-[12px] text-mist">{inline(t.slice(2))}</blockquote>
            );
          if (/^[-*]\s/.test(t))
            return (
              <div key={i} className="flex gap-2.5 text-[13.5px] leading-relaxed text-ghost">
                <span className="mt-0.5 text-mint">·</span>
                <span>{inline(t.replace(/^[-*]\s/, ""))}</span>
              </div>
            );
          if (/^\d+\.\s/.test(t))
            return (
              <div key={i} className="flex gap-2.5 text-[13.5px] leading-relaxed text-ghost">
                <span className="font-mono text-mint/80">{t.match(/^\d+/)?.[0]}.</span>
                <span>{inline(t.replace(/^\d+\.\s/, ""))}</span>
              </div>
            );
          return (
            <p key={i} className="text-[13.5px] leading-relaxed text-ghost">{inline(t)}</p>
          );
        })}
      </div>
      {inv.report_md && (
        <button
          onClick={() => downloadText(`report_${inv.id}.md`, inv.report_md ?? "")}
          className="mt-8 rounded-lg border border-edge-hi px-3 py-1.5 font-mono text-[11px] text-ghost transition hover:border-mint/40 hover:text-mint"
        >
          ↓ report.md
        </button>
      )}
    </Panel>
  );
}

function inline(s: string): ReactNode {
  // **bold** and `code` only — enough for engine markdown, stays tiny
  const parts = s.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**"))
      return <strong key={i} className="font-semibold text-white">{p.slice(2, -2)}</strong>;
    if (p.startsWith("`") && p.endsWith("`"))
      return <code key={i} className="rounded bg-carbon px-1 py-0.5 font-mono text-[12px] text-mint">{p.slice(1, -1)}</code>;
    return <span key={i}>{p}</span>;
  });
}

function ClaimsView({ claims, inv }: { claims: Claim[]; inv: Investigation }) {
  return (
    <div className="space-y-4">
      {claims.map((c) => {
        const d = DIRECTION_META[c.effect_direction] ?? DIRECTION_META.unclear;
        return (
          <Panel key={c.id} className="p-5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[11px] text-mint/80">{c.id}</span>
              <Badge className={d.cls}>
                {d.glyph} {d.label}
              </Badge>
              <Badge className="border-edge-hi text-mist">{fmtEffect(c.effect_size)}</Badge>
              <Badge className="border-edge-hi text-mist">{fmtP(c.p_value)}</Badge>
              {c.sample_size !== null && <Badge className="border-edge-hi text-mist">n = {c.sample_size}</Badge>}
              <Badge
                className={cn(
                  c.confidence === "high" && "border-mint/30 bg-mint/8 text-mint",
                  c.confidence === "medium" && "border-amber-bio/30 bg-amber-bio/8 text-amber-bio",
                  c.confidence === "low" && "border-edge-hi text-mist",
                )}
              >
                {c.confidence}
              </Badge>
            </div>
            <p className="mt-3 text-[14px] leading-relaxed text-white">{c.statement}</p>
            <blockquote className="mt-3 border-l-2 border-mint/40 pl-4 font-mono text-[12px] leading-relaxed text-mist">
              “{c.quote}”
            </blockquote>
            <div className="mt-4 grid gap-2 text-[12px] sm:grid-cols-2 lg:grid-cols-4">
              {[
                ["organism", c.organism],
                ["intervention", c.intervention],
                ["dose", c.dose],
                ["measurement", c.measurement],
              ].map(([k, v]) => (
                <div key={k} className="rounded-lg border border-edge/60 bg-void/50 px-3 py-2">
                  <div className="font-mono text-[10px] uppercase tracking-wider text-mist/70">{k}</div>
                  <div className="mt-0.5 text-ghost">{v || "—"}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 font-mono text-[11px] text-mist">
              ↳ {paperMeta(inv, c.paper_id)}
              {c.statistical_method ? ` · ${c.statistical_method}` : ""}
            </div>
          </Panel>
        );
      })}
    </div>
  );
}

function ConflictsView({ inv }: { inv: Investigation }) {
  if (!inv.conflicts.length) return <Empty text="No cross-study conflicts detected in this corpus." />;
  return (
    <div className="space-y-4">
      {inv.conflicts.map((x) => {
        const v = VERDICT_META[x.verdict] ?? VERDICT_META.ambiguity;
        return (
          <Panel key={x.id} className="p-5">
            <div className="flex flex-wrap items-center gap-3">
              <Badge className={v.cls}>{x.verdict}</Badge>
              <span className="font-mono text-[13px] text-ghost">
                {x.claim_a} <span className="text-rose-bio">↔</span> {x.claim_b}
              </span>
            </div>
            <p className="mt-3 text-[13.5px] leading-relaxed text-ghost">{x.reasoning}</p>
            {x.differences.length > 0 && (
              <div className="mt-4 overflow-hidden rounded-xl border border-edge/60">
                <table className="w-full text-left text-[12px]">
                  <thead>
                    <tr className="border-b border-edge/60 bg-void/60 font-mono text-[10px] uppercase tracking-wider text-mist">
                      <th className="px-4 py-2">factor</th>
                      <th className="px-4 py-2">{x.claim_a}</th>
                      <th className="px-4 py-2">{x.claim_b}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-edge/40">
                    {x.differences.map((d) => (
                      <tr key={d.factor} className="bg-carbon/40">
                        <td className="px-4 py-2 font-mono text-[11px] text-mint/80">{d.factor}</td>
                        <td className="px-4 py-2 text-ghost">{d.a}</td>
                        <td className="px-4 py-2 text-ghost">{d.b}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        );
      })}
    </div>
  );
}

function MechanismsView({ inv }: { inv: Investigation }) {
  return (
    <div className="space-y-4">
      {inv.mechanisms.map((m) => (
        <Panel key={m.id} className="p-5">
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="text-[15px] font-semibold text-white">{m.title}</h3>
            <Badge className="border-bio/30 bg-bio/8 text-bio">{m.hops} hops</Badge>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {m.pathway.map((node, i) => (
              <span key={`${m.id}-${i}`} className="flex items-center gap-2">
                {i > 0 && <span className="text-mint/60">→</span>}
                <span
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-[12px]",
                    i === 0
                      ? "border-edge-hi bg-carbon text-mist"
                      : i === m.pathway.length - 1
                        ? "border-mint/40 bg-mint/8 text-mint"
                        : "border-edge-hi bg-carbon/70 text-ghost",
                  )}
                >
                  {node}
                </span>
              </span>
            ))}
          </div>
          <div className="mt-4 font-mono text-[11px] text-mist">evidence: <span className="text-mint/80">{m.evidence.join(" · ")}</span></div>
        </Panel>
      ))}
    </div>
  );
}

function HypothesesView({ inv }: { inv: Investigation }) {
  return (
    <div className="space-y-4">
      {inv.hypotheses.map((h) => (
        <Panel key={h.id} className="p-5">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-mono text-[11px] text-violet-bio">{h.id}</span>
            <Badge className="border-violet-bio/30 bg-violet-bio/8 text-violet-bio">{h.status}</Badge>
          </div>
          <p className="mt-3 text-[14.5px] leading-relaxed text-white">{h.statement}</p>
          <div className="mt-4 space-y-3 text-[13px]">
            <Row label="mechanism">{h.mechanism}</Row>
            <Row label="predictions">
              <ul className="space-y-1">
                {h.predictions.map((p, i) => (
                  <li key={i} className="flex gap-2"><span className="text-mint">→</span>{p}</li>
                ))}
              </ul>
            </Row>
            <div className="grid gap-3 sm:grid-cols-2">
              <Row label="required measurement">{h.required_measurement}</Row>
              <Row label="expected result">{h.expected_result}</Row>
            </div>
            <Row label="falsification conditions">
              <ul className="space-y-1">
                {h.falsification_conditions.map((f, i) => (
                  <li key={i} className="flex gap-2"><span className="text-rose-bio">✗</span>{f}</li>
                ))}
              </ul>
            </Row>
            <Row label="next experiment">{h.next_experiment}</Row>
          </div>
        </Panel>
      ))}
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-edge/60 bg-void/50 p-3.5">
      <div className="font-mono text-[10px] uppercase tracking-wider text-mist/70">{label}</div>
      <div className="mt-1.5 leading-relaxed text-ghost">{children}</div>
    </div>
  );
}

function GapsView({ inv }: { inv: Investigation }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {inv.gaps.map((g) => (
        <Panel key={g.id} className="p-5">
          <Badge className="border-amber-bio/30 bg-amber-bio/8 text-amber-bio">{g.category}</Badge>
          <p className="mt-3 text-[13.5px] leading-relaxed text-ghost">{g.description}</p>
        </Panel>
      ))}
    </div>
  );
}

function GeoView({ inv }: { inv: Investigation }) {
  if (!inv.geo_closures.length) return <Empty text="No GEO series matched the conflict targets." />;
  return (
    <div className="space-y-4">
      {inv.geo_closures.map((g) => (
        <Panel key={g.id} className="p-5">
          <div className="flex flex-wrap items-center gap-3">
            <Badge className="border-amber-bio/40 bg-amber-bio/8 text-amber-bio font-mono">{g.gse_accession}</Badge>
            <span className="text-[14px] text-white">{g.title}</span>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 font-mono text-[11px] text-mist">
            <Badge className="border-edge-hi">{g.organism}</Badge>
            <Badge className="border-edge-hi">n = {g.n_samples}</Badge>
            <Badge className="border-edge-hi">links: {g.links_claims.join(", ")}</Badge>
          </div>
          <p className="mt-3 text-[13px] leading-relaxed text-mist">{g.resolution}</p>
        </Panel>
      ))}
    </div>
  );
}

function AuditView({ inv }: { inv: Investigation }) {
  if (!inv.audit_flags.length) return <Empty text="Adversarial audit raised no flags." />;
  return (
    <div className="space-y-3">
      {inv.audit_flags.map((a) => {
        const s = SEVERITY_META[a.severity] ?? SEVERITY_META.info;
        return (
          <Panel key={a.id} className="flex items-start gap-4 p-4">
            <Badge className={cn("shrink-0", s.cls)}>{s.label}</Badge>
            <div>
              <span className="font-mono text-[12px] text-mint/80">{a.target}</span>
              <p className="mt-1 text-[13px] leading-relaxed text-ghost">{a.message}</p>
            </div>
          </Panel>
        );
      })}
    </div>
  );
}

function SourcesView({ inv }: { inv: Investigation }) {
  return (
    <div className="space-y-3">
      {inv.papers.map((p) => (
        <Panel key={p.id} className="p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[11px] text-mint/80">{p.id}</span>
            <Badge className="border-edge-hi text-mist">{p.source_db}</Badge>
            {p.is_open_access && <Badge className="border-mint/30 bg-mint/8 text-mint">open access</Badge>}
            <span className="ml-auto font-mono text-[11px] text-mist">relevance {p.relevance.toFixed(2)}</span>
          </div>
          <p className="mt-2 text-[14px] leading-snug text-white">{p.title}</p>
          <p className="mt-1.5 text-[12px] text-mist">
            {p.authors.join(", ")} · {p.journal} · {p.year}
          </p>
          <div className="mt-2 flex flex-wrap gap-3 font-mono text-[11px]">
            <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noreferrer" className="text-bio hover:underline">
              doi:{p.doi}
            </a>
            <a
              href={`https://pubmed.ncbi.nlm.nih.gov/${p.pmid}/`}
              target="_blank"
              rel="noreferrer"
              className="text-bio hover:underline"
            >
              PMID {p.pmid}
            </a>
            {p.pmcid && (
              <a
                href={`https://www.ncbi.nlm.nih.gov/pmc/articles/${p.pmcid}/`}
                target="_blank"
                rel="noreferrer"
                className="text-bio hover:underline"
              >
                {p.pmcid}
              </a>
            )}
          </div>
        </Panel>
      ))}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <Panel className="p-10 text-center">
      <div className="font-mono text-[13px] text-mist">{text}</div>
    </Panel>
  );
}
