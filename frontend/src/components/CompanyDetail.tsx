import { useLocale } from "../i18n/LocaleContext";
import { overallLabel } from "../i18n/locales";
import { evaluateCompliance } from "../lib/compliance";
import type { CompanyDetail as Company } from "../lib/types";
import { CompliancePanel } from "./CompliancePanel";
import { ResultZones } from "./ResultZones";
import { StatusPill } from "./StatusPill";

export function CompanyDetailPane({ company }: { company: Company | null }) {
  const { locale, t } = useLocale();

  if (!company) {
    return (
      <main className="pane">
        <div className="pane-head">
          <h2>{t("detailTitle")}</h2>
        </div>
        <p className="empty">{t("detailEmpty")}</p>
      </main>
    );
  }

  const report = evaluateCompliance(company);

  return (
    <main className="pane">
      <div className="pane-head">
        <h2>{t("detailTitle")}</h2>
        <StatusPill status={company.status} />
      </div>
      <div className="detail">
        <header className="identity">
          <div className="identity-top">
            <h1>{company.legal_name_en || "—"}</h1>
            <span className={`badge ${report.red ? "badge-fail" : "badge-pass"}`}>
              {overallLabel(locale, report.overall)}
            </span>
          </div>
          {company.legal_name_zh ? <p className="zh">{company.legal_name_zh}</p> : null}
          <div className="meta-row">
            <span>
              BRN <code>{company.brn || "—"}</code>
            </span>
            <span>
              {t("trades")}{" "}
              <code>{(company.requested_trades || []).join(", ") || "—"}</code>
            </span>
            {company.seed_only ? <span>{t("statusQueued")}</span> : null}
            {company.live ? <span>Live</span> : null}
          </div>
        </header>

        {company.seed_only ? (
          <p className="empty">{t("seedOnlyHint")}</p>
        ) : (
          <>
            <CompliancePanel report={report} />
            <ResultZones
              evaluations={report.evaluations}
              checks={company.check_results || []}
            />
          </>
        )}
      </div>
    </main>
  );
}
