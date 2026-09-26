import { useEffect, useRef, useState } from "react";
import { STAGES } from "../lib/types";
import { fetchHealth, fetchKeyStatus } from "../lib/api";
import { useEngine } from "../lib/useEngine";
import { cn, fmtLogTime } from "../lib/utils";
import { HelixMark, Kbd, Panel } from "./ui";
import { Report } from "./Report";

const EXAMPLES = [
  "Does hypoxia impair insulin signaling via HIF-1α?",
  "How do intermittent and sustained hypoxia diverge in metabolic outcome?",
  "Which AMPK-mediated effects survive statistical correction?",
];

export function Console({
  goLanding,
  openKeys,
}: {
  goLanding: () => void;
  openKeys: () => void;
}) {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<"pipeline" | "agent">("pipeline");
  const [health, setHealth] = useState<{ online: boolean; demo: boolean } | null>(null);
  const [keys, setKeys] = useState<{ ready: boolean; any: boolean } | null>(null);
  const { investigation, phase, currentStage, completedStages, logs, progress, error, run, reset } = useEngine();
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchHealth().then((h) =>
      setHealth(h ? { online: true, demo: h.demo_mode } : { online: false, demo: true }),
    );
  }, []);

  // Re-check key status on mount and whenever keys are saved in the modal.
  useEffect(() => {
    let alive = true;
    fetchKeyStatus().then((k) => {
      if (alive) setKeys(k ? { ready: k.ready, any: k.groq || k.nvidia || k.gemini } : null);
    });
    const onKeysChanged = () => {
      fetchKeyStatus().then((k) => {
        if (alive)
          setKeys(k ? { ready: k.ready, any: k.groq || k.nvidia || k.gemini } : null);
      });
    };
    window.addEventListener("biosynthetica:keys-changed", onKeysChanged);
    return () => {
      alive = false;
      window.removeEventListener("biosynthetica:keys-changed", onKeysChanged);
    };
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [logs.length]);

  const needsKey = health?.online === true && keys !== null && !keys.any;

  function submit() {
    if (!question.trim() || phase === "running" || needsKey) return;
    run(question.trim(), mode);
  }

  const running = phase === "running";
  const done = phase === "complete" && investigation !== null;

  return (
    <main className="relative mx-auto min-h-screen max-w-6xl px-5 pb-24 pt-24">
      <div className="bg-grid absolute inset-x-0 top-0 h-72" aria-hidden />
      <div
        className="absolute -top-24 left-1/2 h-72 w-[700px] -translate-x-1/2 rounded-full bg-mint/8 blur-[120px]"
        aria-hidden
      />

      {/* header row */}
      <div className="relative flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <HelixMark className="h-7 w-7" />
            <h1 className="font-display text-2xl text-white">Investigation console</h1>
          </div>
          <p className="mt-1.5 font-mono text-[12px] text-mist">
            {health === null
              ? "probing research engine…"
              : health.online
                ? `engine online${health.demo ? " · demo-mode LLMs" : ""}`
                : "engine offline — demo replay active"}
          </p>
          <div
            className={cn(
              "mt-2 inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[11px]",
              health?.online
                ? "border-mint/30 bg-mint/8 text-mint"
                : "border-amber-bio/30 bg-amber-bio/8 text-amber-bio",
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                health?.online ? "bg-mint animate-pulse-soft" : "bg-amber-bio",
              )}
            />            
            {health?.online
              ? needsKey
                ? "no key set — add one to run"
                : "live retrieval ready"
              : "static mode · scripted replay"}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={openKeys}
            title="LLM API keys"
            className="rounded-full border border-edge-hi px-3.5 py-2 font-mono text-[12px] text-mist transition hover:border-mint/40 hover:text-mint"
          >
            🔑 keys
          </button>
          <button
            onClick={goLanding}
            className="rounded-full border border-edge-hi px-4 py-2 font-mono text-[12px] text-mist transition hover:border-mint/40 hover:text-white"
          >
            ← back to overview
          </button>
        </div>
      </div>

      {/* composer */}
      <Panel className="relative mt-8 p-5" glow>
        <label className="font-mono text-[11px] uppercase tracking-[0.2em] text-mist">
          research question
        </label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={3}
          placeholder="e.g. Does hypoxia impair insulin signaling via HIF-1α?"
          className="mt-3 w-full resize-none rounded-xl border border-edge/70 bg-void/70 p-4 text-[15px] leading-relaxed text-white placeholder:text-mist/50 outline-none transition focus:border-mint/50 focus:shadow-[0_0_0_3px_rgba(61,255,178,0.08)]"
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => setQuestion(ex)}
              className="rounded-full border border-edge/70 px-3 py-1.5 text-[11.5px] text-mist transition hover:border-mint/40 hover:text-ghost"
            >
              {ex.length > 46 ? ex.slice(0, 46) + "…" : ex}
            </button>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-1 rounded-full border border-edge/70 bg-void/60 p-1">
            {(["pipeline", "agent"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={cn(
                  "rounded-full px-4 py-1.5 font-mono text-[12px] transition",
                  mode === m ? "bg-mint/15 text-mint" : "text-mist hover:text-ghost",
                )}
              >
                {m === "pipeline" ? "pipeline" : "agent · ReAct"}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden font-mono text-[11px] text-mist sm:block">
              <Kbd>Enter</Kbd> run · <Kbd>Shift</Kbd>+<Kbd>Enter</Kbd> newline
            </span>
            {done && (
              <button
                onClick={reset}
                className="rounded-full border border-edge-hi px-4 py-2 font-mono text-[12px] text-mist transition hover:border-rose-bio/40 hover:text-rose-bio"
              >
                clear
              </button>
            )}
            <button
              onClick={needsKey ? openKeys : submit}
              disabled={running || (!question.trim() && !needsKey)}
              className={cn(
                "rounded-full px-6 py-2.5 font-mono text-[13px] font-semibold transition-all",
                running || (!question.trim() && !needsKey)
                  ? "cursor-not-allowed border border-edge-hi bg-carbon text-mist/50"
                  : needsKey
                    ? "border border-amber-bio/50 bg-amber-bio/15 text-amber-bio hover:bg-amber-bio/25"
                    : "bg-mint text-void hover:shadow-[0_0_32px_-8px_rgba(61,255,178,0.7)]",
              )}
            >
              {running
                ? "investigating…"
                : needsKey
                  ? "🔑 add a key to run"
                  : done
                    ? "re-run"
                    : "investigate →"}
            </button>
          </div>
        </div>
      </Panel>

      {/* progress + stage rail */}
      {(running || done) && (
        <div className="mt-6 h-1 overflow-hidden rounded-full bg-carbon">
          <div
            className="h-full rounded-full bg-gradient-to-r from-mint-deep via-mint to-bio transition-all duration-700"
            style={{ width: `${Math.max(running ? 6 : 100, progress)}%` }}
          />
        </div>
      )}
      {(running || done) && (
        <div className="mt-6 grid gap-2 sm:grid-cols-4 lg:grid-cols-8">
          {STAGES.map((s, i) => {
            const isDone = completedStages.includes(s.key);
            const isNow = currentStage === s.key;
            return (
              <div
                key={s.key}
                className={cn(
                  "hairline relative overflow-hidden rounded-xl px-3 py-2.5 transition-all duration-300",
                  isDone && "border-mint/25 bg-mint/5",
                  isNow && "border-mint/50 bg-mint/10 shadow-[0_0_24px_-10px_rgba(61,255,178,0.6)]",
                  !isDone && !isNow && "bg-carbon/50 opacity-60",
                )}
              >
                {isNow && <span className="absolute inset-x-0 top-0 h-0.5 mint-flow" />}
                <div className="flex items-center justify-between gap-1">
                  <span className="font-mono text-[10px] text-mist">{String(i + 1).padStart(2, "0")}</span>
                  <span
                    className={cn(
                      "font-mono text-[10px]",
                      isDone ? "text-mint" : isNow ? "animate-pulse-soft text-mint" : "text-mist/40",
                    )}
                  >
                    {isDone ? "✓" : isNow ? "◉" : "·"}
                  </span>
                </div>
                <div className={cn("mt-1 text-[11.5px] leading-tight", isNow || isDone ? "text-white" : "text-mist")}>
                  {s.label}
                </div>
                <div className="mt-0.5 font-mono text-[9.5px] text-mist/60">{s.detail}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* run log */}
      {(running || logs.length > 0) && !done && (
        <Panel className="mt-6 overflow-hidden">
          <div className="flex items-center justify-between border-b border-edge/60 px-4 py-2.5">
            <span className="font-mono text-[11px] text-mist">live run log</span>
            <span className="font-mono text-[10px] text-mist/60">{logs.length} events</span>
          </div>
          <div ref={logRef} className="max-h-56 overflow-y-auto px-4 py-3 font-mono text-[12px] leading-6">
            {logs.map((l) => (
              <div key={l.id} className="flex gap-3">
                <span className="shrink-0 text-mist/50">{fmtLogTime(l.t)}</span>
                <span
                  className={cn(
                    "shrink-0",
                    l.level === "flag" ? "text-rose-bio" : l.level === "warn" ? "text-amber-bio" : "text-mint/80",
                  )}
                >
                  {l.level === "flag" ? "⚑" : l.level === "warn" ? "▲" : "·"}
                </span>
                <span className={cn(l.level === "flag" ? "text-rose-bio/90" : "text-ghost")}>{l.message}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {error && (
        <Panel className="mt-6 border-rose-bio/40 p-5">
          <div className="font-mono text-[12px] text-rose-bio">✗ {error}</div>
        </Panel>
      )}

      {done && investigation && (
        <div className="mt-6">
          <Report inv={investigation} />
        </div>
      )}
    </main>
  );
}
