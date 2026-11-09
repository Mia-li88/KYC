import type { ComplianceReport } from "../lib/types";
import { complianceGates } from "../lib/compliance";

export function CompliancePanel({ report }: { report: ComplianceReport }) {
  return (
    <section className={`compliance-banner ${report.red ? "red" : "ok"}`}>
      <div className="compliance-title">
        <strong>{report.overall === "红灯" ? "紅燈" : "達標"}</strong>
        <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
          {complianceGates.title_zh}
        </span>
      </div>
      <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--ink-soft)" }}>
        {complianceGates.red_light_policy.zh}
      </p>

      <div className="gate-grid">
        {report.evaluations.map((e) => {
          const cls =
            e.verdict === "达标" ? "ok" : e.verdict === "欠缺" ? "bad" : "na";
          return (
            <div key={e.gate_id} className={`gate-chip ${cls}`}>
              <span className="verdict">{e.verdict}</span>
              <strong style={{ fontSize: "0.82rem" }}>{e.label_zh}</strong>
            </div>
          );
        })}
      </div>

      {report.gaps.length > 0 ? (
        <div>
          <h3 style={{ margin: "0.2rem 0", fontSize: "0.78rem", letterSpacing: "0.08em" }}>
            GAP LIST
          </h3>
          <ol className="gap-list">
            {report.gaps.map((g) => (
              <li key={g.gate_id}>
                <strong>{g.label_zh}</strong> — {g.reason_zh}
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <p style={{ margin: 0, color: "var(--ok)", fontWeight: 600 }}>全部必填門檻達標</p>
      )}
    </section>
  );
}
