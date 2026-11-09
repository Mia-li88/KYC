import type { AccessClass, CheckResult } from "../lib/types";

const GROUPS: { key: AccessClass; title: string }[] = [
  { key: "auto", title: "Auto" },
  { key: "semi", title: "Semi" },
  { key: "hitl", title: "HITL" },
];

function Badge({ status }: { status: string }) {
  const s = status || "pending";
  return <span className={`badge badge-${s}`}>{s}</span>;
}

function dedupeLatest(results: CheckResult[]): CheckResult[] {
  const map = new Map<string, CheckResult>();
  for (const r of results) map.set(r.tool, r);
  return [...map.values()];
}

export function CheckCards({ results }: { results: CheckResult[] }) {
  const unique = dedupeLatest(results);
  return (
    <div className="section">
      {GROUPS.map((g) => {
        const items = unique.filter((r) => r.access_class === g.key);
        if (!items.length) return null;
        return (
          <section key={g.key} className="section">
            <h3>{g.title}</h3>
            <div className="check-grid">
              {items.map((r, idx) => (
                <article key={`${r.tool}-${idx}`} className="check-card">
                  <header>
                    <span className="tool">{r.tool}</span>
                    <Badge status={String(r.status)} />
                  </header>
                  <p>{r.summary || "—"}</p>
                </article>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
