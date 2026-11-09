import type { QueueStatus } from "../lib/types";

const LABELS: Record<string, string> = {
  running_auto: "Running Auto",
  awaiting_hitl: "Awaiting HITL",
  summarized: "Summarized",
};

export function StatusPill({ status }: { status: QueueStatus }) {
  const key = String(status || "running_auto");
  return (
    <span className={`status-pill status-${key}`}>{LABELS[key] || key}</span>
  );
}
