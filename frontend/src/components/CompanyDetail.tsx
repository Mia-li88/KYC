import type { CompanyDetail as Company } from "../lib/types";
import { evaluateCompliance } from "../lib/compliance";
import { CheckCards } from "./CheckCards";
import { CompliancePanel } from "./CompliancePanel";
import { StatusPill } from "./StatusPill";

export function CompanyDetailPane({ company }: { company: Company | null }) {
  if (!company) {
    return (
      <main className="pane">
        <div className="pane-head">
          <h2>Company detail</h2>
        </div>
        <p className="empty">Select a company from the queue, or start a new check.</p>
      </main>
    );
  }

  const report = evaluateCompliance(company);

  return (
    <main className="pane">
      <div className="pane-head">
        <h2>Company detail</h2>
        <StatusPill status={company.status} />
      </div>
      <div className="detail">
        <header className="identity">
          <div className="identity-top">
            <h1>{company.legal_name_en || "—"}</h1>
            {report.red ? (
              <span className="badge badge-fail">紅燈</span>
            ) : (
              <span className="badge badge-pass">達標</span>
            )}
          </div>
          {company.legal_name_zh ? <p className="zh">{company.legal_name_zh}</p> : null}
          <div className="meta-row">
            <span>
              BRN <code>{company.brn || "—"}</code>
            </span>
            <span>
              Trades{" "}
              <code>{(company.requested_trades || []).join(", ") || "—"}</code>
            </span>
            {company.fixture ? <span>Fixture demo</span> : null}
          </div>
        </header>

        <CompliancePanel report={report} />
        <CheckCards results={company.check_results || []} />
      </div>
    </main>
  );
}
