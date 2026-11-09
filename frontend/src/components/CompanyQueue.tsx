import { useState } from "react";
import { useLocale } from "../i18n/LocaleContext";
import type { QueueCompany } from "../lib/types";
import { StatusPill } from "./StatusPill";

interface Props {
  companies: QueueCompany[];
  selectedId?: string | null;
  onSelect: (threadId: string) => void;
  onStart: (payload: {
    brn: string;
    legal_name_en: string;
    legal_name_zh: string;
    trades: string[];
    offline: boolean;
  }) => void;
  busy?: boolean;
}

export function CompanyQueue({ companies, selectedId, onSelect, onStart, busy }: Props) {
  const { t } = useLocale();
  const [brn, setBrn] = useState("FAKE1234");
  const [en, setEn] = useState("DEMO BUILDING CO LTD");
  const [zh, setZh] = useState("示范建筑有限公司");
  const [trades, setTrades] = useState("electrical,general");
  const [offline, setOffline] = useState(true);

  return (
    <aside className="pane">
      <div className="pane-head">
        <h2>{t("queueTitle")}</h2>
        <span>{companies.length}</span>
      </div>

      <form
        className="new-run"
        onSubmit={(e) => {
          e.preventDefault();
          onStart({
            brn: brn.trim(),
            legal_name_en: en.trim(),
            legal_name_zh: zh.trim(),
            trades: trades.split(",").map((t) => t.trim()).filter(Boolean),
            offline,
          });
        }}
      >
        <strong style={{ fontSize: "0.85rem" }}>{t("startCheck")}</strong>
        <input value={brn} onChange={(e) => setBrn(e.target.value)} placeholder={t("placeholderBrn")} />
        <input value={en} onChange={(e) => setEn(e.target.value)} placeholder={t("placeholderNameEn")} />
        <input value={zh} onChange={(e) => setZh(e.target.value)} placeholder={t("placeholderNameZh")} />
        <input
          value={trades}
          onChange={(e) => setTrades(e.target.value)}
          placeholder={t("placeholderTrades")}
        />
        <label className="confirm">
          <input type="checkbox" checked={offline} onChange={(e) => setOffline(e.target.checked)} />
          {t("offline")}
        </label>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? t("runBusy") : t("runSubmit")}
        </button>
      </form>

      <ul className="queue-list">
        {companies.map((c) => (
          <li key={c.thread_id}>
            <button
              type="button"
              className={`queue-item ${selectedId === c.thread_id ? "active" : ""}`}
              onClick={() => onSelect(c.thread_id)}
            >
              <span className="queue-brn">{c.brn || "—"}</span>
              <span className="queue-name">{c.legal_name_en || t("unnamedCompany")}</span>
              {c.legal_name_zh ? <span className="queue-name-zh">{c.legal_name_zh}</span> : null}
              <StatusPill status={c.status} />
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
