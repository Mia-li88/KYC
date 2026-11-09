import { useLocale } from "../i18n/LocaleContext";
import { checkStatusLabel } from "../i18n/locales";
import type { AccessClass, CheckResult } from "../lib/types";

function dedupeLatest(results: CheckResult[]): CheckResult[] {
  const map = new Map<string, CheckResult>();
  for (const r of results) map.set(r.tool, r);
  return [...map.values()];
}

export function CheckCards({ results }: { results: CheckResult[] }) {
  const { locale, t } = useLocale();
  const unique = dedupeLatest(results);
  const groups: { key: AccessClass; title: string }[] = [
    { key: "auto", title: t("groupAuto") },
    { key: "semi", title: t("groupSemi") },
    { key: "hitl", title: t("groupHitl") },
  ];

  return (
    <div className="section">
      {groups.map((g) => {
        const items = unique.filter((r) => r.access_class === g.key);
        if (!items.length) return null;
        return (
          <section key={g.key} className="section">
            <h3>{g.title}</h3>
            <div className="check-grid">
              {items.map((r, idx) => {
                const status = String(r.status || "pending");
                return (
                  <article key={`${r.tool}-${idx}`} className="check-card">
                    <header>
                      <span className="tool">{r.tool}</span>
                      <span className={`badge badge-${status}`}>
                        {checkStatusLabel(locale, status)}
                      </span>
                    </header>
                    <p>{r.summary || "—"}</p>
                  </article>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
