export type Locale = "zh-CN" | "en";

export const DEFAULT_LOCALE: Locale = "zh-CN";

const zhCN = {
  brand: "KYC",
  brandAccent: "审查工作台",
  tagline: "香港建造业分判商预审 — Auto / Semi / HITL 检查与合规门槛（达标 · 欠缺 · 红灯）",
  refreshQueue: "刷新队列",
  langEn: "EN",
  langZh: "中文",
  langToggleAria: "切换语言",

  queueTitle: "公司队列",
  startCheck: "开始检查",
  placeholderBrn: "商业登记号码 (BRN)",
  placeholderNameEn: "英文名称",
  placeholderNameZh: "中文名称",
  placeholderTrades: "工种：electrical,general",
  liveOnlyHint: "始终调用实时开放数据 API（公司注册处 / 机电署 / 劳工处等）；网络失败会显示为错误／红灯。",
  runBusy: "运行中…",
  runSubmit: "运行 Auto → Semi → HITL",
  runSubmitLive: "实时检查 Auto → Semi → HITL",
  unnamedCompany: "未命名公司",

  statusRunningAuto: "自动检查中",
  statusAwaitingHitl: "待人工确认",
  statusSummarized: "已汇总",
  statusQueued: "待实时检查",

  detailTitle: "公司详情",
  detailEmpty: "请从左侧队列选择公司，或开始新的检查。",
  seedOnlyHint: "此为队列种子条目，尚未运行实时检查。请在左侧填写后点击「实时检查」。",
  trades: "工种",
  fixtureDemo: "演示数据",
  overallPass: "达标",
  overallRed: "红灯",
  verdictPass: "达标",
  verdictGap: "欠缺",
  verdictNa: "不适用",
  gapList: "缺口清单",
  allGatesPass: "全部必填门槛达标",
  zoneNotPass: "未达标",
  zoneNa: "不适用",
  zonePass: "达标",
  zoneLeftEmpty: "暂无未达标或不适用项",
  zoneRightEmpty: "暂无达标项",
  itemGate: "门槛",
  itemCheck: "检查",

  groupAuto: "自动 (Auto)",
  groupSemi: "半自动 (Semi)",
  groupHitl: "人工 (HITL)",

  checkStatusPass: "通过",
  checkStatusFail: "失败",
  checkStatusWarn: "警告",
  checkStatusPending: "待处理",
  checkStatusSkipped: "已跳过",
  checkStatusError: "错误",
  checkStatusAwaitingHuman: "待人工",
  checkStatusStub: "桩实现",

  hitlTitle: "HITL 上传",
  hitlConfirm: "确认并继续",
  hitlResuming: "恢复中…",
  hitlNoCompany: "未选择公司。",
  hitlInterruptedEmpty: "图已中断，但未返回待办项。",
  hitlNonePending: "暂无待上传 HITL 文件。中断／恢复对应 LangGraph Command(resume=…)。",
  hitlUploaded: "已上传：",
  hitlReviewerConfirmed: "审查员已确认",

  apiDownHint: "— 请先在 :8000 启动 API",
} as const;

const en: { [K in keyof typeof zhCN]: string } = {
  brand: "KYC",
  brandAccent: "Workbench",
  tagline:
    "Hong Kong construction subcontractor review — Auto / Semi / HITL checks with compliance gating (Pass · Gap · Red flag).",
  refreshQueue: "Refresh queue",
  langEn: "EN",
  langZh: "中文",
  langToggleAria: "Switch language",

  queueTitle: "Company queue",
  startCheck: "Start check",
  placeholderBrn: "BRN",
  placeholderNameEn: "English name",
  placeholderNameZh: "Chinese name",
  placeholderTrades: "trades: electrical,general",
  liveOnlyHint:
    "Always calls live open-data APIs (CR / EMSD / LD, etc.); network failures surface as errors / red flags.",
  runBusy: "Running…",
  runSubmit: "Run Auto → Semi → HITL",
  runSubmitLive: "Live check Auto → Semi → HITL",
  unnamedCompany: "Unnamed company",

  statusRunningAuto: "Running Auto",
  statusAwaitingHitl: "Awaiting HITL",
  statusSummarized: "Summarized",
  statusQueued: "Queued for live check",

  detailTitle: "Company detail",
  detailEmpty: "Select a company from the queue, or start a new check.",
  seedOnlyHint:
    "Seed queue entry — no live check yet. Use the left form and click Live check.",
  trades: "Trades",
  fixtureDemo: "Fixture demo",
  overallPass: "Pass",
  overallRed: "Red flag",
  verdictPass: "Pass",
  verdictGap: "Gap",
  verdictNa: "N/A",
  gapList: "Gap list",
  allGatesPass: "All required gates passed",
  zoneNotPass: "Not met",
  zoneNa: "N/A",
  zonePass: "Pass",
  zoneLeftEmpty: "No gaps or N/A items",
  zoneRightEmpty: "No passing items yet",
  itemGate: "Gate",
  itemCheck: "Check",

  groupAuto: "Auto",
  groupSemi: "Semi",
  groupHitl: "HITL",

  checkStatusPass: "pass",
  checkStatusFail: "fail",
  checkStatusWarn: "warn",
  checkStatusPending: "pending",
  checkStatusSkipped: "skipped",
  checkStatusError: "error",
  checkStatusAwaitingHuman: "awaiting human",
  checkStatusStub: "stub",

  hitlTitle: "HITL upload",
  hitlConfirm: "Confirm & resume",
  hitlResuming: "Resuming…",
  hitlNoCompany: "No company selected.",
  hitlInterruptedEmpty: "Graph is interrupted but no pending items were returned.",
  hitlNonePending:
    "No pending HITL documents. Interrupt/resume maps to LangGraph Command(resume=…).",
  hitlUploaded: "Uploaded: ",
  hitlReviewerConfirmed: "Reviewer confirmed",

  apiDownHint: "— start the API on :8000",
};

export type MessageKey = keyof typeof zhCN;

export const messages: Record<Locale, Record<MessageKey, string>> = {
  "zh-CN": zhCN,
  en,
};

export function verdictLabel(
  locale: Locale,
  verdict: "达标" | "欠缺" | "不适用" | string,
): string {
  const m = messages[locale];
  if (verdict === "达标") return m.verdictPass;
  if (verdict === "欠缺") return m.verdictGap;
  if (verdict === "不适用") return m.verdictNa;
  return verdict;
}

export function overallLabel(locale: Locale, overall: "红灯" | "达标" | string): string {
  const m = messages[locale];
  if (overall === "红灯") return m.overallRed;
  if (overall === "达标") return m.overallPass;
  return overall;
}

export function statusLabel(locale: Locale, status: string): string {
  const m = messages[locale];
  switch (status) {
    case "running_auto":
      return m.statusRunningAuto;
    case "awaiting_hitl":
      return m.statusAwaitingHitl;
    case "summarized":
      return m.statusSummarized;
    case "queued":
      return m.statusQueued;
    default:
      return status;
  }
}

export function checkStatusLabel(locale: Locale, status: string): string {
  const m = messages[locale];
  switch (status) {
    case "pass":
      return m.checkStatusPass;
    case "fail":
      return m.checkStatusFail;
    case "warn":
      return m.checkStatusWarn;
    case "pending":
      return m.checkStatusPending;
    case "skipped":
      return m.checkStatusSkipped;
    case "error":
      return m.checkStatusError;
    case "awaiting_human":
      return m.checkStatusAwaitingHuman;
    case "stub":
      return m.checkStatusStub;
    default:
      return status;
  }
}
