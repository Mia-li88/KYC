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

function thresholds(gate: ComplianceGate): Pick<GateEvaluation, "threshold_zh" | "threshold_en"> {
  return {
    threshold_zh: gate.threshold_zh,
    threshold_en: gate.threshold_en,
  };
}

function resultFromCheck(
  check: CheckResult | undefined,
  fallbackZh: string,
  fallbackEn: string,
): Pick<GateEvaluation, "result_zh" | "result_en"> {
  const summary = check?.summary?.trim();
  if (summary) {
    return { result_zh: summary, result_en: summary };
  }
  return { result_zh: fallbackZh, result_en: fallbackEn };
}

function evaluateGate(
  gate: ComplianceGate,
  company: CompanyDetail,
  byTool: Map<string, CheckResult>,
): GateEvaluation {
  const trades = company.requested_trades || [];
  const applicable = gateApplies(gate, trades);
  const base = {
    gate_id: gate.id,
    label_zh: gate.label_zh,
    label_en: gate.label_en,
    tool: gate.tool,
    ...thresholds(gate),
  };

  if (!applicable) {
    return {
      ...base,
      applicable: false,
      verdict: "不适用",
      red: false,
      result_zh: "本查询未申请相关工种，此项不适用。",
      result_en: "Related trade not requested for this query — N/A.",
      reason_zh: "工种条件不适用",
      reason_en: "Trade condition not applicable",
    };
  }

  const tool = gate.tool || "";
  const check = byTool.get(tool);
  const status = check?.status ? String(check.status) : undefined;

  if (!check || !status) {
    return {
      ...base,
      applicable: true,
      verdict: "欠缺",
      red: true,
      check_status: "missing",
      result_zh: `无检查结果（工具 ${tool || "—"}）`,
      result_en: `No check result (tool ${tool || "—"})`,
      reason_zh: gate.gap_hint_zh,
      reason_en: gate.gap_hint_en,
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

  const result = resultFromCheck(check, `状态：${status}`, `Status: ${status}`);

  if ((pass || stubOk) && !dataFail && !fail) {
    return {
      ...base,
      applicable: true,
      verdict: "达标",
      red: false,
      check_status: status,
      ...result,
      reason_zh: check.summary || "通过",
      reason_en: check.summary || "Pass",
    };
  }

  if (
    fail ||
    dataFail ||
    (unknown && gate.unknown_as_red) ||
    (!pass && !stubOk && gate.unknown_as_red !== false && !unknown)
  ) {
    return {
      ...base,
      applicable: true,
      verdict: "欠缺",
      red: true,
      check_status: status,
      ...result,
      reason_zh: gate.gap_hint_zh,
      reason_en: gate.gap_hint_en,
    };
  }

  if (unknown && !gate.unknown_as_red) {
    return {
      ...base,
      applicable: true,
      verdict: "达标",
      red: false,
      check_status: status,
      ...result,
      reason_zh: check.summary || status,
      reason_en: check.summary || status,
    };
  }

  return {
    ...base,
    applicable: true,
    verdict: "欠缺",
    red: true,
    check_status: status,
    ...result,
    reason_zh: gate.gap_hint_zh,
    reason_en: gate.gap_hint_en,
  };
}

/** Compare check results against editable compliance_gates config (per item). */
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
