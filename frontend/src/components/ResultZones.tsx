import { useLocale } from "../i18n/LocaleContext";
import { checkStatusLabel, verdictLabel } from "../i18n/locales";
import type { CheckResult, GateEvaluation } from "../lib/types";

type ZoneKind = "not_pass" | "na" | "pass";

interface ZoneItem {
  id: string;
  kind: ZoneKind;
  source: "gate" | "check";
  title: string;
  subtitle: string;
  badge: string;
  accessClass?: string;
}

function dedupeChecks(results: CheckResult[]): CheckResult[] {
  const map = new Map<string, CheckResult>();
  for (const r of results) map.set(r.tool, r);
  return [...map.values()];
}

function checkZone(status: string): ZoneKind {
  if (status === "pass") return "pass";
  if (status === "skipped") return "na";
  return "not_pass";
}

function ZoneCard({ item }: { item: ZoneItem }) {
  const tone =
    item.kind === "pass" ? "pass" : item.kind === "na" ? "na" : "not-pass";
  return (
    <article className={`zone-card zone-card-${tone}`}>
      <header>
        <span className="zone-card-meta">
          {item.source === "gate" ? item.accessClass || "gate" : item.accessClass}
        </span>
        <span className={`badge badge-${item.kind === "pass" ? "pass" : item.kind === "na" ? "skipped" : "fail"}`}>
          {item.badge}
        </span>
      </header>
      <strong className="zone-card-title">{item.title}</strong>
      <p>{item.subtitle}</p>
    </article>
  );
}

export function ResultZones({
  evaluations,
  checks,
}: {
  evaluations: GateEvaluation[];
  checks: CheckResult[];
}) {
  const { locale, t } = useLocale();

  const gateItems: ZoneItem[] = evaluations.map((e) => {
    const kind: ZoneKind =
      e.verdict === "达标" ? "pass" : e.verdict === "不适用" ? "na" : "not_pass";
    return {
      id: `gate-${e.gate_id}`,
      kind,
      source: "gate",
      title: locale === "en" ? e.label_en : e.label_zh,
      subtitle: locale === "en" ? e.reason_en : e.reason_zh,
      badge: verdictLabel(locale, e.verdict),
      accessClass: t("itemGate"),
    };
  });

  const checkItems: ZoneItem[] = dedupeChecks(checks).map((c) => {
    const status = String(c.status || "pending");
    const kind = checkZone(status);
    return {
      id: `check-${c.tool}`,
      kind,
      source: "check",
      title: c.tool,
      subtitle: c.summary || "—",
      badge: checkStatusLabel(locale, status),
      accessClass: `${t("itemCheck")} · ${c.access_class}`,
    };
  });

  const all = [...gateItems, ...checkItems];
  const left = all.filter((i) => i.kind === "not_pass" || i.kind === "na");
  const right = all.filter((i) => i.kind === "pass");
  const leftFail = left.filter((i) => i.kind === "not_pass");
  const leftNa = left.filter((i) => i.kind === "na");

  return (
    <div className="result-zones">
      <section className="result-zone result-zone-left" aria-label={t("zoneNotPass")}>
        <div className="result-zone-head">
          <h3>
            {t("zoneNotPass")}
            <span className="zone-sep">·</span>
            {t("zoneNa")}
          </h3>
          <span className="zone-count">{left.length}</span>
        </div>
        {left.length === 0 ? (
          <p className="empty">{t("zoneLeftEmpty")}</p>
        ) : (
          <div className="zone-stack">
            {leftFail.length > 0 ? (
              <div className="zone-stack-group">
                <h4>{t("zoneNotPass")}</h4>
                {leftFail.map((item) => (
                  <ZoneCard key={item.id} item={item} />
                ))}
              </div>
            ) : null}
            {leftNa.length > 0 ? (
              <div className="zone-stack-group">
                <h4>{t("zoneNa")}</h4>
                {leftNa.map((item) => (
                  <ZoneCard key={item.id} item={item} />
                ))}
              </div>
            ) : null}
          </div>
        )}
      </section>

      <section className="result-zone result-zone-right" aria-label={t("zonePass")}>
        <div className="result-zone-head">
          <h3>{t("zonePass")}</h3>
          <span className="zone-count">{right.length}</span>
        </div>
        {right.length === 0 ? (
          <p className="empty">{t("zoneRightEmpty")}</p>
        ) : (
          <div className="zone-stack">
            {right.map((item) => (
              <ZoneCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
