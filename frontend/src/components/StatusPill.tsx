import { useLocale } from "../i18n/LocaleContext";
import { statusLabel } from "../i18n/locales";
import type { QueueStatus } from "../lib/types";

export function StatusPill({ status }: { status: QueueStatus }) {
  const { locale } = useLocale();
  const key = String(status || "running_auto");
  return (
    <span className={`status-pill status-${key}`}>{statusLabel(locale, key)}</span>
  );
}
