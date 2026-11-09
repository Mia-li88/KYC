import gatesConfig from "../config/compliance_gates.json";
import type {
  CheckResult,
  CompanyDetail,
  ComplianceGate,
  ComplianceGatesConfig,
  ComplianceReport,
  GateEvaluation,
} from "./types";

export const complianceGates = gatesConfig as ComplianceGatesConfig;

function latestByTool(results: CheckResult[]): Map<string, CheckResult> {
  const map = new Map<string, CheckResult>();
  for (const r of results) {
    map.set(r.tool, r);
  }
  return map;
}

function gateApplies(gate: ComplianceGate, trades: string[]): boolean {
  if (gate.when?.always) return true;
  const needed = gate.when?.trades_any || [];
  if (!needed.length) return true;
  const set = new Set(trades.map((t) => t.toLowerCase()));
  return needed.some((t) => set.has(t.toLowerCase()));
}

function matchCount(check?: CheckResult): number | undefined {
  if (!check?.data) return undefined;
  const raw = check.data.match_count;
  return typeof raw === "number" ? raw : undefined;
}

function evaluateGate(
  gate: ComplianceGate,
  company: CompanyDetail,
  byTool: Map<string, CheckResult>,
): GateEvaluation {
  const trades = company.requested_trades || [];
  const applicable = gateApplies(gate, trades);

  if (!applicable) {
    return {
      gate_id: gate.id,
      label_zh: gate.label_zh,
      label_en: gate.label_en,
      applicable: false,
      verdict: "不适用",
      red: false,
      tool: gate.tool,
      reason_zh: "工種條件不適用",
      reason_en: "Trade condition not applicable",
    };
  }

  if (gate.type === "hitl_pending") {
    const pending = (company.pending_human || []).filter((p) => !p.resolved);
    const awaitingChecks = (company.check_results || []).filter(
      (c) => c.access_class === "hitl" && c.status === "awaiting_human",
    );
    const open = pending.length > 0 || awaitingChecks.length > 0 || !!company.awaiting_human;
    if (open) {
      const names = pending.map((p) => p.id).join(", ") || awaitingChecks.map((c) => c.tool).join(", ");
      return {
        gate_id: gate.id,
        label_zh: gate.label_zh,
        label_en: gate.label_en,
        applicable: true,
        verdict: "欠缺",
        red: true,
        reason_zh: `${gate.gap_hint_zh}（${names || "pending"}）`,
        reason_en: `${gate.gap_hint_en} (${names || "pending"})`,
      };
    }
    return {
      gate_id: gate.id,
      label_zh: gate.label_zh,
      label_en: gate.label_en,
      applicable: true,
      verdict: "达标",
      red: false,
      reason_zh: "必要 HITL 文件已確認",
      reason_en: "Required HITL documents confirmed",
    };
  }

  const tool = gate.tool || "";
  const check = byTool.get(tool);
  const status = check?.status ? String(check.status) : undefined;

  if (!check || !status) {
    return {
      gate_id: gate.id,
      label_zh: gate.label_zh,
      label_en: gate.label_en,
      applicable: true,
      verdict: "欠缺",
      red: true,
      tool,
      check_status: "missing",
      reason_zh: `${gate.gap_hint_zh} — 無檢查結果（工具 ${tool}）`,
      reason_en: `${gate.gap_hint_en} — no check result (tool ${tool})`,
    };
  }

  const pass = (gate.pass_statuses || ["pass"]).includes(status);
  const fail = (gate.fail_statuses || ["fail", "error"]).includes(status);
  const unknown = (gate.unknown_statuses || []).includes(status);
  const stubOk = gate.allow_stub_pass && status === "stub";

  let dataFail = false;
  if (gate.require_data?.match_count_max !== undefined) {
    const count = matchCount(check);
    if (count === undefined && !stubOk) {
      dataFail = true;
    } else if (typeof count === "number" && count > gate.require_data.match_count_max) {
      dataFail = true;
    }
  }

  if ((pass || stubOk) && !dataFail && !fail) {
    return {
      gate_id: gate.id,
      label_zh: gate.label_zh,
      label_en: gate.label_en,
      applicable: true,
      verdict: "达标",
      red: false,
      tool,
      check_status: status,
      reason_zh: check.summary || "通過",
      reason_en: check.summary || "Pass",
    };
  }

  if (fail || dataFail || (unknown && gate.unknown_as_red) || (!pass && !stubOk && gate.unknown_as_red !== false && !unknown)) {
    const proved = check.summary || status;
    return {
      gate_id: gate.id,
      label_zh: gate.label_zh,
      label_en: gate.label_en,
      applicable: true,
      verdict: "欠缺",
      red: true,
      tool,
      check_status: status,
      reason_zh: `${gate.gap_hint_zh} — 證明：${tool} → ${proved}`,
      reason_en: `${gate.gap_hint_en} — proved by ${tool} → ${proved}`,
    };
  }

  // Unknown but not red (e.g. stub allowed without counting as pass when allow_stub_pass false)
  if (unknown && !gate.unknown_as_red) {
    return {
      gate_id: gate.id,
      label_zh: gate.label_zh,
      label_en: gate.label_en,
      applicable: true,
      verdict: "达标",
      red: false,
      tool,
      check_status: status,
      reason_zh: `暫以 stub／未知放行（非紅燈策略）：${check.summary || status}`,
      reason_en: `Stub/unknown allowed (non-red policy): ${check.summary || status}`,
    };
  }

  return {
    gate_id: gate.id,
    label_zh: gate.label_zh,
    label_en: gate.label_en,
    applicable: true,
    verdict: "欠缺",
    red: true,
    tool,
    check_status: status,
    reason_zh: `${gate.gap_hint_zh} — 證明：${tool} → ${check.summary || status}`,
    reason_en: `${gate.gap_hint_en} — proved by ${tool} → ${check.summary || status}`,
  };
}

/** Compare check results against editable compliance_gates config. */
export function evaluateCompliance(company: CompanyDetail): ComplianceReport {
  const byTool = latestByTool(company.check_results || []);
  const evaluations = complianceGates.gates.map((g) => evaluateGate(g, company, byTool));
  const gaps = evaluations.filter((e) => e.applicable && e.red);
  const red = gaps.length > 0;
  return {
    overall: red ? "红灯" : "达标",
    red,
    gaps,
    evaluations,
  };
}
