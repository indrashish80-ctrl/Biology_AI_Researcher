import { useCallback, useRef, useState } from "react";
import type { Investigation, JobEvent, LogEvent } from "./types";
import { startInvestigation } from "./api";

export type RunPhase = "idle" | "running" | "complete" | "error";

let logSeq = 0;

export function useEngine() {
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [phase, setPhase] = useState<RunPhase>("idle");
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [completedStages, setCompletedStages] = useState<string[]>([]);
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef<(() => void) | null>(null);
  const stageRef = useRef<string | null>(null);
  const finishedRef = useRef(false);

  const handleEvent = useCallback((e: JobEvent) => {
    if (e.type === "stage") {
      const prev = stageRef.current;
      if (prev && prev !== e.stage) setCompletedStages((c) => (c.includes(prev) ? c : [...c, prev]));
      stageRef.current = e.stage;
      setCurrentStage(e.stage);
      if (typeof e.progress === "number") setProgress(e.progress);
      pushLog({ level: "info", message: e.message || stageLabel(e.stage) });
    } else if (e.type === "log") {
      pushLog(e);
    } else if (e.type === "done") {
      // Idempotency guard: ignore duplicate done events (SSE replay safety).
      if (finishedRef.current) return;
      finishedRef.current = true;
      const prev = stageRef.current;
      if (prev) setCompletedStages((c) => (c.includes(prev) ? c : [...c, prev]));
      stageRef.current = null;
      setCurrentStage(null);
      setProgress(100);
      setInvestigation(e.investigation);
      setPhase("complete");
    } else {
      setError(e.message);
      setPhase("error");
    }
  }, []);

  function pushLog(e: { level: LogEvent["level"]; message: string }) {
    logSeq += 1;
    const id = logSeq;
    setLogs((l) => [...l.slice(-220), { id, t: Date.now(), ...e }]);
  }

  const run = useCallback(
    (question: string, mode: "pipeline" | "agent") => {
      cancelRef.current?.();
      setInvestigation(null);
      setPhase("running");
      setCompletedStages([]);
      setLogs([]);
      setProgress(0);
      setError(null);
      stageRef.current = null;
      finishedRef.current = false;
      setCurrentStage(null);
      cancelRef.current = startInvestigation(question, mode, handleEvent);
    },
    [handleEvent],
  );

  const reset = useCallback(() => {
    cancelRef.current?.();
    cancelRef.current = null;
    stageRef.current = null;
    finishedRef.current = false;
    setInvestigation(null);
    setPhase("idle");
    setCurrentStage(null);
    setCompletedStages([]);
    setLogs([]);
    setProgress(0);
    setError(null);
  }, []);

  return { investigation, phase, currentStage, completedStages, logs, progress, error, run, reset };
}

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    startup: "Starting the research engine",
    engine: "Engine initializing",
    retrieval: "Acquiring literature from open databases",
    extraction: "Extracting quote-grounded claims",
    contradictions: "Detecting cross-study contradictions",
    geo: "Closing the loop with GEO datasets",
    pathways: "Synthesizing mechanistic pathways",
    hypotheses: "Formulating falsifiable hypotheses",
    audit: "Running adversarial audit",
    report: "Assembling research dossier",
    agent: "Autonomous agent running",
    complete: "Investigation complete",
    error: "Engine error",
  };
  return map[stage] ?? (stage ? stage.replace(/_/g, " ") : "working");
}
