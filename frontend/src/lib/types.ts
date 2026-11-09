export type QueueStatus =
  | "queued"
  | "running_auto"
  | "awaiting_hitl"
  | "summarized"
  | string;

export type AccessClass = "auto" | "semi" | "hitl";

export type CheckStatus =
  | "pass"
  | "fail"
  | "warn"
  | "pending"
  | "skipped"
  | "error"
  | "awaiting_human"
  | "stub";

export interface CheckResult {
  tool: string;
  access_class: AccessClass;
  status: CheckStatus | string;
  summary?: string;
  data?: Record<string, unknown>;
  source_urls?: string[];
  notes?: string[];
}

export interface PendingHumanItem {
  id: string;
  kind: string;
  prompt: string;
  upload_paths?: string[];
  resolved?: boolean;
  resolution?: Record<string, unknown> | null;
  created_at?: string | null;
}

export interface QueueCompany {
  thread_id: string;
  brn?: string | null;
  legal_name_en?: string | null;
  legal_name_zh?: string | null;
  status: QueueStatus;
  requested_trades?: string[];
  fixture?: boolean;
  seed_only?: boolean;
  summary?: string | null;
}

export interface CompanyDetail extends QueueCompany {
  aliases?: string[];
  trade_reg_nos?: string[];
  auto_done?: boolean;
  semi_done?: boolean;
  hitl_done?: boolean;
  awaiting_human?: boolean;
  interrupted?: boolean;
  interrupt_message?: string;
  errors?: string[];
  network_errors?: string[];
  check_results?: CheckResult[];
  pending_human?: PendingHumanItem[];
  live?: boolean;
}

export interface GateWhen {
  always?: boolean;
  trades_any?: string[];
}

export interface ComplianceGate {
  id: string;
  label_zh: string;
  label_en: string;
  required: boolean;
  when: GateWhen;
  tool?: string;
  type?: "hitl_pending" | string;
  pass_statuses?: string[];
  fail_statuses?: string[];
  unknown_statuses?: string[];
  unknown_as_red?: boolean;
  allow_stub_pass?: boolean;
  require_data?: { match_count_max?: number };
  gap_hint_zh: string;
  gap_hint_en: string;
}

export interface ComplianceGatesConfig {
  version: number;
  title_zh: string;
  title_en: string;
  source_docs: string[];
  red_light_policy: { zh: string; en: string };
  gates: ComplianceGate[];
}

export type GateVerdict = "达标" | "欠缺";

export interface GateEvaluation {
  gate_id: string;
  label_zh: string;
  label_en: string;
  applicable: boolean;
  verdict: GateVerdict | "不适用";
  red: boolean;
  tool?: string;
  check_status?: string;
  reason_zh: string;
  reason_en: string;
}

export interface ComplianceReport {
  overall: "红灯" | "达标";
  red: boolean;
  gaps: GateEvaluation[];
  evaluations: GateEvaluation[];
}
