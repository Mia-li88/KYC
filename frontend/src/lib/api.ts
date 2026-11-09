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
  thread_id?: string;
}): Promise<CompanyDetail> {
  // Always live Auto/Semi — no HITL document upload path.
  return request("/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...body,
      offline: false,
      require_financials: false,
      require_insurance: false,
      require_safety_docs: false,
      require_track_record: false,
    }),
  });
}
