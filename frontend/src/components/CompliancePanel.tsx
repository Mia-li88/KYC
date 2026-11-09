import { useLocale } from "../i18n/LocaleContext";
import { overallLabel } from "../i18n/locales";
import { complianceGates } from "../lib/compliance";
import type { ComplianceReport } from "../lib/types";

/** Summary banner + gap list only; gate chips live in ResultZones. */
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
