import type { ReactNode } from "react";
import { cn } from "../lib/utils";

export function Badge({
  children,
  className,
  mono = true,
}: {
  children: ReactNode;
  className?: string;
  mono?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] tracking-wide whitespace-nowrap",
        mono && "font-mono",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Panel({
  children,
  className,
  glow = false,
}: {
  children: ReactNode;
  className?: string;
  glow?: boolean;
}) {
  return (
    <div
      className={cn(
        "glass rounded-2xl",
        glow && "shadow-[0_0_60px_-18px_rgba(61,255,178,0.25)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function SectionTitle({
  kicker,
  title,
  className,
  right,
}: {
  kicker?: string;
  title: ReactNode;
  className?: string;
  right?: ReactNode;
}) {
  return (
    <div className={cn("flex items-end justify-between gap-6", className)}>
      <div>
        {kicker && (
          <div className="font-mono text-[11px] uppercase tracking-[0.28em] text-mint/80 mb-3">
            {kicker}
          </div>
        )}
        <h2 className="font-display text-3xl sm:text-4xl text-white">{title}</h2>
      </div>
      {right}
    </div>
  );
}

export function Stat({
  value,
  label,
  accent = "text-mint",
}: {
  value: ReactNode;
  label: string;
  accent?: string;
}) {
  return (
    <div className="hairline rounded-xl bg-carbon/60 px-4 py-3">
      <div className={cn("font-mono text-xl font-semibold", accent)}>{value}</div>
      <div className="mt-1 text-[11px] uppercase tracking-[0.18em] text-mist">{label}</div>
    </div>
  );
}

export function HelixMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden>
      <path d="M8 2c0 8 16 12 16 20a8 8 0 0 1-16 0" stroke="url(#hg1)" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M24 2c0 8-16 12-16 20a8 8 0 0 0 16 0" stroke="url(#hg2)" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M10.5 8h11M9 14h14M10.5 20h11M12.5 26h7" stroke="#3dffb2" strokeWidth="1.2" strokeLinecap="round" opacity="0.75" />
      <defs>
        <linearGradient id="hg1" x1="8" y1="2" x2="24" y2="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="#63e6ff" />
          <stop offset="1" stopColor="#3dffb2" />
        </linearGradient>
        <linearGradient id="hg2" x1="24" y1="2" x2="8" y2="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="#3dffb2" />
          <stop offset="1" stopColor="#a78bfa" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export function Spark({ className }: { className?: string }) {
  return <span className={cn("inline-block h-1.5 w-1.5 rounded-full bg-mint animate-pulse-soft", className)} />;
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded-md border border-edge-hi bg-carbon px-1.5 py-0.5 font-mono text-[10px] text-mist">
      {children}
    </kbd>
  );
}
