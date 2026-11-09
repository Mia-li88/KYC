import { useCallback, useEffect, useMemo, useState } from "react";
import { CompanyDetailPane } from "./components/CompanyDetail";
import { CompanyQueue } from "./components/CompanyQueue";
import { HitlPanel } from "./components/HitlPanel";
import { useLocale } from "./i18n/LocaleContext";
import { getCompany, listCompanies, startRun } from "./lib/api";
import type { CompanyDetail, QueueCompany } from "./lib/types";
import "./styles/workbench.css";

function toQueueRow(company: CompanyDetail): QueueCompany {
  return {
    thread_id: company.thread_id,
    brn: company.brn,
    legal_name_en: company.legal_name_en,
    legal_name_zh: company.legal_name_zh,
    status: company.status,
    requested_trades: company.requested_trades,
    fixture: company.fixture,
    seed_only: company.seed_only,
    summary: company.summary,
  };
}

export default function App() {
  const { locale, setLocale, t } = useLocale();
  const [queue, setQueue] = useState<QueueCompany[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CompanyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selectedCompany = useMemo(
    () => queue.find((c) => c.thread_id === selectedId) || null,
    [queue, selectedId],
  );

  const refreshQueue = useCallback(async () => {
    const rows = await listCompanies();
    setQueue(rows);
    return rows;
  }, []);

  const loadDetail = useCallback(async (threadId: string) => {
    const company = await getCompany(threadId);
    setDetail(company);
    setSelectedId(threadId);
    setQueue((prev) => {
      const others = prev.filter((p) => p.thread_id !== threadId);
      return [toQueueRow(company), ...others];
    });
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale === "zh-CN" ? "zh-Hans" : "en";
  }, [locale]);

  useEffect(() => {
    (async () => {
      try {
        const rows = await refreshQueue();
        if (rows[0]) {
          await loadDetail(rows[0].thread_id);
        }
      } catch (err) {
        setError(
          err instanceof Error ? `${err.message} ${t("apiDownHint")}` : String(err),
        );
      }
    })();
  }, [refreshQueue, loadDetail, t]);

  async function onSelect(threadId: string) {
    setError(null);
    try {
      await loadDetail(threadId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onStart(payload: {
    brn: string;
    legal_name_en: string;
    legal_name_zh: string;
    trades: string[];
    thread_id?: string;
  }) {
    setBusy(true);
    setError(null);
    try {
      const company = await startRun({
        brn: payload.brn || undefined,
        legal_name_en: payload.legal_name_en || undefined,
        legal_name_zh: payload.legal_name_zh || undefined,
        requested_trades: payload.trades,
        require_track_record: false,
        thread_id: payload.thread_id,
      });
      setDetail(company);
      setSelectedId(company.thread_id);
      await refreshQueue();
      if (company.network_errors?.length || company.errors?.length) {
        const errs = company.network_errors || company.errors || [];
        setError(errs.join("; "));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function onHitlUpdated(company: CompanyDetail) {
    setDetail(company);
    setQueue((prev) => {
      const others = prev.filter((p) => p.thread_id !== company.thread_id);
      return [toQueueRow(company), ...others];
    });
  }

  return (
    <div className="workbench">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand">
            {t("brand")} <span>{t("brandAccent")}</span>
          </div>
          <p className="tagline">{t("tagline")}</p>
        </div>
        <div className="top-actions">
          <div className="lang-toggle" role="group" aria-label={t("langToggleAria")}>
            <button
              type="button"
              className={`btn lang-btn ${locale === "zh-CN" ? "active" : ""}`}
              onClick={() => setLocale("zh-CN")}
            >
              {t("langZh")}
            </button>
            <button
              type="button"
              className={`btn lang-btn ${locale === "en" ? "active" : ""}`}
              onClick={() => setLocale("en")}
            >
              {t("langEn")}
            </button>
          </div>
          <button
            className="btn"
            type="button"
            onClick={() => refreshQueue().catch((e) => setError(String(e)))}
          >
            {t("refreshQueue")}
          </button>
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <div className="panes">
        <CompanyQueue
          companies={queue}
          selectedId={selectedId}
          selectedCompany={selectedCompany}
          onSelect={onSelect}
          onStart={onStart}
          busy={busy}
        />
        <CompanyDetailPane company={detail} />
        <HitlPanel company={detail} onUpdated={onHitlUpdated} setError={setError} />
      </div>
    </div>
  );
}
