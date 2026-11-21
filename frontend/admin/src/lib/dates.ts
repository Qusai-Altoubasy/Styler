import type { Lang } from "@styler/shared/i18n/setup";

/**
 * Order dates in Jordan's time, like the "today" count the server computes
 * (Asia/Amman), with Latin digits as everywhere else in the app.
 */
export function formatDateTime(iso: string, lang: Lang): string {
  return new Intl.DateTimeFormat(lang === "ar" ? "ar-JO-u-nu-latn" : "en-GB", {
    timeZone: "Asia/Amman",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}
