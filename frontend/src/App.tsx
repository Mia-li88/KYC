import { useCallback, useEffect, useState } from "react";
import { CompanyDetailPane } from "./components/CompanyDetail";
import { CompanyQueue } from "./components/CompanyQueue";
import { HitlPanel } from "./components/HitlPanel";
import { getCompany, listCompanies, startRun } from "./lib/api";
import type { CompanyDetail, QueueCompany } from "./lib/types";
import "./styles/workbench.css";

export default function App() {
  const [queue, setQueue] = useState<QueueCompany[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CompanyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
      return [
        {
          thread_id: company.thread_id,
          brn: company.brn,
          legal_name_en: company.legal_name_en,
          legal_name_zh: company.legal_name_zh,
          status: company.status,
          requested_trades: company.requested_trades,
          fixture: company.fixture,
          summary: company.summary,
        },
        ...others,
      ];
    });
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const rows = await refreshQueue();
        if (rows[0]) {
          await loadDetail(rows[0].thread_id);
        }
      } catch (err) {
        setError(
          err instanceof Error
            ? `${err.message} — start the API on :8000`
            : String(err),
        );
      }
    })();
  }, [refreshQueue, loadDetail]);

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
    offline: boolean;
  }) {
    setBusy(true);
    setError(null);
    try {
      const company = await startRun({
        brn: payload.brn || undefined,
        legal_name_en: payload.legal_name_en || undefined,
        legal_name_zh: payload.legal_name_zh || undefined,
        requested_trades: payload.trades,
        offline: payload.offline,
        require_track_record: false,
      });
      setDetail(company);
      setSelectedId(company.thread_id);
      await refreshQueue();
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
      return [
        {
          thread_id: company.thread_id,
          brn: company.brn,
          legal_name_en: company.legal_name_en,
          legal_name_zh: company.legal_name_zh,
          status: company.status,
          requested_trades: company.requested_trades,
          fixture: company.fixture,
          summary: company.summary,
        },
        ...others,
      ];
    });
  }

  return (
    <div className="workbench">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand">
            KYC <span>Workbench</span>
          </div>
          <p className="tagline">
            Hong Kong construction subcontractor review — Auto / Semi / HITL checks with
            compliance gating (達標 · 欠缺 · 紅燈).
          </p>
        </div>
        <div className="top-actions">
          <button
            className="btn"
            type="button"
            onClick={() => refreshQueue().catch((e) => setError(String(e)))}
          >
            Refresh queue
          </button>
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <div className="panes">
        <CompanyQueue
          companies={queue}
          selectedId={selectedId}
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
