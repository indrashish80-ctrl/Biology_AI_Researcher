import { useEffect, useState } from "react";
import { HelixMark } from "./ui";
import { cn } from "../lib/utils";

export type Route = "landing" | "console";

export function Nav({
  route,
  go,
  openKeys,
}: {
  route: Route;
  go: (r: Route) => void;
  openKeys: () => void;
}) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-all duration-300",
        scrolled ? "glass border-x-0 border-t-0" : "bg-transparent",
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <button onClick={() => go("landing")} className="group flex items-center gap-2.5">
          <HelixMark className="h-7 w-7 transition-transform duration-500 group-hover:rotate-180" />
          <span className="font-display text-lg tracking-wide text-white">
            Bio<span className="text-mint">Synthetica</span>
          </span>
        </button>

        {route === "landing" && (
          <nav className="hidden items-center gap-7 text-[13px] text-mist md:flex">
            <a href="#capabilities" className="transition hover:text-white">
              Capabilities
            </a>
            <a href="#pipeline" className="tag-hover">
              Pipeline
            </a>
            <a href="#evidence" className="tag-hover">
              Evidence
            </a>
            <a href="#api" className="tag-hover">
              API
            </a>
          </nav>
        )}

        <div className="flex items-center gap-2.5">
          <button
            onClick={openKeys}
            title="LLM API keys"
            className="rounded-full border border-edge-hi px-3.5 py-2 font-mono text-[12px] text-mist transition hover:border-mint/40 hover:text-mint"
          >
            🔑 keys
          </button>
          <button
            onClick={() => go("console")}
            className={cn(
              "group relative overflow-hidden rounded-full border px-4 py-2 font-mono text-[13px] font-medium transition-all",
              route === "console"
                ? "border-mint/50 bg-mint/15 text-mint"
                : "border-mint/40 bg-mint/10 text-mint hover:bg-mint/20 hover:shadow-[0_0_24px_-6px_rgba(61,255,178,0.5)]",
            )}
          >
            <span className="relative z-10">{route === "console" ? "● console" : "Open console"}</span>
          </button>
          {route === "landing" && (
            <span className="hidden text-[12px] text-mist/70 md:inline" aria-hidden>
              ·
            </span>
          )}
        </div>
      </div>
      <style>{`.tag-hover{transition:color .2s}.tag-hover:hover{color:#fff}`}</style>
    </header>
  );
}
