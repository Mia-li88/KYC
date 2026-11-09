import { useLocale } from "../i18n/LocaleContext";
import { overallLabel, verdictLabel } from "../i18n/locales";
import { complianceGates } from "../lib/compliance";
import type { ComplianceReport } from "../lib/types";

export function CompliancePanel({ report }: { report: ComplianceReport }) {
  const { locale, t } = useLocale();
  const title =
    locale === "en" ? complianceGates.title_en : complianceGates.title_zh;
  const policy =
    locale === "en"
      ? complianceGates.red_light_policy.en
      : complianceGates.red_light_policy.zh;

  return (
    <section className={`compliance-banner ${report.red ? "red" : "ok"}`}>
      <div className="compliance-title">
        <strong>{overallLabel(locale, report.overall)}</strong>
        <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>{title}</span>
      </div>
      <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--ink-soft)" }}>{policy}</p>

      <div className="gate-grid">
        {report.evaluations.map((e) => {
          const cls =
            e.verdict === "达标" ? "ok" : e.verdict === "欠缺" ? "bad" : "na";
          const label = locale === "en" ? e.label_en : e.label_zh;
          return (
            <div key={e.gate_id} className={`gate-chip ${cls}`}>
              <span className="verdict">{verdictLabel(locale, e.verdict)}</span>
              <strong style={{ fontSize: "0.82rem" }}>{label}</strong>
            </div>
          );
        })}
      </div>

      {report.gaps.length > 0 ? (
        <div>
          <h3 style={{ margin: "0.2rem 0", fontSize: "0.78rem", letterSpacing: "0.08em" }}>
            {t("gapList")}
          </h3>
          <ol className="gap-list">
            {report.gaps.map((g) => (
              <li key={g.gate_id}>
                <strong>{locale === "en" ? g.label_en : g.label_zh}</strong>
                {" — "}
                {locale === "en" ? g.reason_en : g.reason_zh}
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <p style={{ margin: 0, color: "var(--ok)", fontWeight: 600 }}>{t("allGatesPass")}</p>
      )}
    </section>
  );
}
