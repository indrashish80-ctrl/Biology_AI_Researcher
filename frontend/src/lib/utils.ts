export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function fmtDate(unix: number): string {
  return new Date(unix).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtLogTime(unix: number): string {
  const d = new Date(unix);
  return (
    String(d.getHours()).padStart(2, "0") +
    ":" +
    String(d.getMinutes()).padStart(2, "0") +
    ":" +
    String(d.getSeconds()).padStart(2, "0")
  );
}

export function fmtP(p: number | null): string {
  if (p === null || p === undefined) return "—";
  if (p < 0.001) return "p < 0.001";
  return `p = ${p.toFixed(3)}`;
}

export function fmtEffect(size: number | null): string {
  if (size === null || size === undefined || Number.isNaN(size)) return "—";
  const s = size > 0 ? `+${size.toFixed(2)}` : size.toFixed(2);
  return s;
}

export const DIRECTION_META: Record<string, { label: string; cls: string; glyph: string }> = {
  increase: { label: "increase", cls: "text-bio border-bio/30 bg-bio/8", glyph: "↑" },
  decrease: { label: "decrease", cls: "text-amber-bio border-amber-bio/30 bg-amber-bio/8", glyph: "↓" },
  no_effect: { label: "no effect", cls: "text-mist border-edge-hi bg-edge/40", glyph: "→" },
  unclear: { label: "unclear", cls: "text-mist border-edge-hi bg-edge/40", glyph: "?" },
};

export const VERDICT_META: Record<string, { label: string; cls: string }> = {
  contradiction: { label: "contradiction", cls: "text-rose-bio border-rose-bio/40 bg-rose-bio/8" },
  conflict: { label: "conflict", cls: "text-amber-bio border-amber-bio/30 bg-amber-bio/8" },
  ambiguity: { label: "ambiguity", cls: "text-violet-bio border-violet-bio/30 bg-violet-bio/8" },
};

export const SEVERITY_META: Record<string, { cls: string; label: string }> = {
  critical: { label: "critical", cls: "text-rose-bio border-rose-bio/40 bg-rose-bio/8" },
  warn: { label: "warning", cls: "text-amber-bio border-amber-bio/30 bg-amber-bio/8" },
  info: { label: "info", cls: "text-bio border-bio/30 bg-bio/8" },
};

export function slug(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
}

export function downloadJson(name: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadText(name: string, text: string): void {
  const blob = new Blob([text], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
