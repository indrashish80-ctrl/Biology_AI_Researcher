import { useEffect, useState } from "react";
import { fetchKeyStatus, saveKeys, type KeyStatus } from "../lib/api";
import { cn } from "../lib/utils";
import { Badge, Panel } from "./ui";

const PROVIDERS = [
  {
    field: "groq_key" as const,
    name: "Groq",
    model: "openai/gpt-oss-20b · 120b",
    url: "https://console.groq.com/keys",
    urlLabel: "console.groq.com/keys",
    accent: "text-mint border-mint/30 bg-mint/8",
    blurb: "Recommended — free tier, fastest. Handles the bulk of extraction & synthesis calls.",
  },
  {
    field: "nvidia_key" as const,
    name: "NVIDIA NIM",
    model: "nemotron-3-super-120b",
    url: "https://build.nvidia.com/",
    urlLabel: "build.nvidia.com",
    accent: "text-bio border-bio/30 bg-bio/8",
    blurb: "Fallback provider — kicks in automatically when Groq rate-limits (429).",
  },
  {
    field: "gemini_key" as const,
    name: "Google Gemini",
    model: "gemini-2.0 / 2.5-flash",
    url: "https://aistudio.google.com/apikey",
    urlLabel: "aistudio.google.com/apikey",
    accent: "text-violet-bio border-violet-bio/30 bg-violet-bio/8",
    blurb: "Last resort in the cascade — generous free tier, slower on bursts.",
  },
];

const STATUS_KEY = { groq_key: "groq", nvidia_key: "nvidia", gemini_key: "gemini" } as const;

/**
 * Modal for BYO-key management. Talks to the engine's /api/keys endpoints:
 * GET (booleans only — never values), POST, DELETE.
 */
export function KeyManager({ onClose }: { onClose: () => void }) {
  const [status, setStatus] = useState<KeyStatus | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    fetchKeyStatus().then(setStatus);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit() {
    setBusy(true);
    setMsg(null);
    const payload: Record<string, string> = {};
    for (const [k, v] of Object.entries(values)) {
      if (v.trim()) payload[k] = v.trim();
    }
    if (!Object.keys(payload).length) {
      setBusy(false);
      setMsg("Paste at least one key first.");
      return;
    }
    const next = await saveKeys(payload);
    setBusy(false);
    if (next) {
      setStatus(next);
      setValues({});
      setMsg(
        next.ready
          ? "Saved — the engine will use your key(s). You can close this and run."
          : "Saved, but no key registered yet — paste at least one valid key.",
      );
      // Tell listeners (Console gate) to re-check key status.
      window.dispatchEvent(new Event("biosynthetica:keys-changed"));
    } else {
      setMsg("Could not reach the engine. Keys can only be set when the backend is running.");
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-void/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <Panel
        className="animate-rise max-h-[88vh] w-full max-w-xl overflow-y-auto p-6"
        glow
      >
        <div onClick={(e) => e.stopPropagation()}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-mint/80">
                bring your own key
              </div>
              <h2 className="mt-2 font-display text-2xl text-white">LLM API keys</h2>
            </div>
            <button
              onClick={onClose}
              className="rounded-full border border-edge-hi px-3 py-1.5 font-mono text-[12px] text-mist transition hover:border-rose-bio/40 hover:text-rose-bio"
            >
              esc
            </button>
          </div>

          <p className="mt-4 text-[13px] leading-relaxed text-mist">
            The engine cascades across providers — first available wins, and it fails over
            automatically on rate limits. Keys are stored server-side and are{" "}
            <span className="text-ghost">never echoed back</span> to the browser. Literature
            retrieval (PubMed, Europe PMC, Crossref, GEO) needs no key.
          </p>

          <div className="mt-5 flex flex-wrap gap-2">
            {PROVIDERS.map((p) => (
              <Badge
                key={p.field}
                className={cn(status?.[STATUS_KEY[p.field]] ? p.accent : "border-edge-hi text-mist/60")}
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    status?.[STATUS_KEY[p.field]] ? "bg-current" : "bg-mist/40",
                  )}
                />
                {p.name} {status?.[STATUS_KEY[p.field]] ? "· set" : "· not set"}
              </Badge>
            ))}
          </div>

          <div className="mt-5 space-y-4">
            {PROVIDERS.map((p) => (
              <div key={p.field} className="rounded-xl border border-edge/70 bg-void/60 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className={cn("rounded border px-1.5 py-0.5 font-mono text-[10px]", p.accent)}>
                      {p.name}
                    </span>
                    <span className="font-mono text-[11px] text-mist">{p.model}</span>
                  </div>
                  <a
                    href={p.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-mono text-[11px] text-bio hover:underline"
                  >
                    get a key ↗ {p.urlLabel.replace(/^https?:\/\//, "")}
                  </a>
                </div>
                <p className="mt-2 text-[12px] leading-relaxed text-mist">{p.blurb}</p>
                <input
                  type="password"
                  value={values[p.field] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [p.field]: e.target.value }))}
                  placeholder={
                    status?.[STATUS_KEY[p.field]]
                      ? "•••••••• (set — paste to replace)"
                      : `paste ${p.name} key…`
                  }
                  className="mt-3 w-full rounded-lg border border-edge/70 bg-carbon/70 px-3 py-2 font-mono text-[12.5px] text-white placeholder:text-mist/40 outline-none transition focus:border-mint/50"
                  autoComplete="off"
                />
              </div>
            ))}
          </div>

          {msg && (
            <div className="mt-4 rounded-lg border border-mint/25 bg-mint/5 px-3.5 py-2.5 font-mono text-[11.5px] text-mint">
              {msg}
            </div>
          )}

          <div className="mt-5 flex items-center justify-end gap-2">
              <button onClick={onClose} className="rounded-full px-4 py-2 font-mono text-[12px] text-mist hover:text-white">
                close
              </button>
              <button
                onClick={submit}
                disabled={busy}
                className="rounded-full bg-mint px-5 py-2 font-mono text-[12.5px] font-semibold text-void transition hover:shadow-[0_0_28px_-8px_rgba(61,255,178,0.7)] disabled:opacity-40"
              >
                {busy ? "saving…" : "save keys"}
              </button>
          </div>
        </div>
      </Panel>
    </div>
  );
}
