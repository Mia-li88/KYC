import type { CompanyDetail, QueueCompany } from "./types";

/** Empty = same-origin / Vite proxy; override with VITE_API_BASE for direct API. */
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function listCompanies(): Promise<QueueCompany[]> {
  return request("/companies");
}

export function getCompany(threadId: string): Promise<CompanyDetail> {
  return request(`/companies/${encodeURIComponent(threadId)}`);
}

export function startRun(body: {
  brn?: string;
  legal_name_en?: string;
  legal_name_zh?: string;
  requested_trades?: string[];
  offline?: boolean;
  thread_id?: string;
  require_track_record?: boolean;
}): Promise<CompanyDetail> {
  return request("/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function resumeRun(
  threadId: string,
  resume: Record<string, unknown>,
): Promise<CompanyDetail> {
  return request(`/runs/${encodeURIComponent(threadId)}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume }),
  });
}

export async function uploadFile(
  threadId: string,
  pendingId: string,
  file: File,
): Promise<{ path: string; filename: string; pending_id: string }> {
  const form = new FormData();
  form.append("pending_id", pendingId);
  form.append("file", file);
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(threadId)}/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}
