import { useMemo, useState } from "react";
import { useLocale } from "../i18n/LocaleContext";
import { resumeRun, uploadFile } from "../lib/api";
import type { CompanyDetail, PendingHumanItem } from "../lib/types";

interface Props {
  company: CompanyDetail | null;
  onUpdated: (company: CompanyDetail) => void;
  setError: (msg: string | null) => void;
}

interface Draft {
  path?: string;
  filename?: string;
  confirmed: boolean;
}

export function HitlPanel({ company, onUpdated, setError }: Props) {
  const { t } = useLocale();
  const pending = useMemo(
    () => (company?.pending_human || []).filter((p) => !p.resolved),
    [company],
  );
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [busy, setBusy] = useState(false);

  const canConfirm =
    pending.length > 0 &&
    pending.every((p) => drafts[p.id]?.path && drafts[p.id]?.confirmed);

  async function onFile(item: PendingHumanItem, file: File | null) {
    if (!company || !file) return;
    setError(null);
    try {
      const uploaded = await uploadFile(company.thread_id, item.id, file);
      setDrafts((d) => ({
        ...d,
        [item.id]: {
          ...(d[item.id] || { confirmed: false }),
          path: uploaded.path,
          filename: uploaded.filename,
        },
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function confirmAll() {
    if (!company) return;
    setBusy(true);
    setError(null);
    try {
      if (company.fixture) {
        const updated: CompanyDetail = {
          ...company,
          awaiting_human: false,
          interrupted: false,
          status: "summarized",
          hitl_done: true,
          summary: company.summary || "Fixture HITL confirmed (local demo)",
          pending_human: (company.pending_human || []).map((p) => ({
            ...p,
            resolved: true,
            upload_paths: drafts[p.id]?.path ? [drafts[p.id].path!] : p.upload_paths,
            resolution: {
              paths: drafts[p.id]?.path ? [drafts[p.id].path!] : [],
              confirmed: true,
            },
          })),
          check_results: (company.check_results || []).map((c) =>
            c.access_class === "hitl" && c.status === "awaiting_human"
              ? { ...c, status: "pass", summary: "Confirmed in workbench (fixture)" }
              : c,
          ),
        };
        onUpdated(updated);
        return;
      }

      const resume: Record<string, { paths: string[]; confirmed: boolean }> = {};
      for (const p of pending) {
        const d = drafts[p.id];
        if (!d?.path) continue;
        resume[p.id] = { paths: [d.path], confirmed: !!d.confirmed };
      }
      const next = await resumeRun(company.thread_id, resume);
      onUpdated(next);
      setDrafts({});
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="pane hitl-pane">
      <div className="pane-head">
        <h2>{t("hitlTitle")}</h2>
        <button
          className="btn btn-accent"
          type="button"
          disabled={!canConfirm || busy}
          onClick={confirmAll}
        >
          {busy ? t("hitlResuming") : t("hitlConfirm")}
        </button>
      </div>
      <div className="hitl-body">
        {!company ? (
          <p className="empty">{t("hitlNoCompany")}</p>
        ) : pending.length === 0 ? (
          <p className="empty">
            {company.awaiting_human ? t("hitlInterruptedEmpty") : t("hitlNonePending")}
          </p>
        ) : (
          <>
            {company.interrupt_message ? (
              <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.86rem" }}>
                {company.interrupt_message}
              </p>
            ) : null}
            {pending.map((item) => {
              const draft = drafts[item.id] || { confirmed: false };
              return (
                <article key={item.id} className="hitl-card">
                  <h4>{item.kind}</h4>
                  <p>{item.prompt}</p>
                  <code style={{ fontSize: "0.75rem", color: "var(--muted)" }}>{item.id}</code>
                  <input
                    type="file"
                    onChange={(e) => onFile(item, e.target.files?.[0] || null)}
                  />
                  {draft.filename ? (
                    <span style={{ fontSize: "0.8rem" }}>
                      {t("hitlUploaded")}
                      {draft.filename}
                    </span>
                  ) : null}
                  <label className="confirm">
                    <input
                      type="checkbox"
                      checked={!!draft.confirmed}
                      onChange={(e) =>
                        setDrafts((d) => ({
                          ...d,
                          [item.id]: { ...(d[item.id] || {}), confirmed: e.target.checked },
                        }))
                      }
                    />
                    {t("hitlReviewerConfirmed")}
                  </label>
                </article>
              );
            })}
          </>
        )}
      </div>
    </aside>
  );
}
