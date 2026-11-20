import i18n, { type Resource } from "i18next";
import { initReactI18next } from "react-i18next";

export type Lang = "ar" | "en";

const STORAGE_KEY = "styler.lang";

export function savedLang(): Lang {
  return localStorage.getItem(STORAGE_KEY) === "en" ? "en" : "ar";
}

function applyDocument(lang: Lang) {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
}

/** Arabic by default. Each app passes its namespaces (one per feature). */
export function initI18n(resources: Resource) {
  const lang = savedLang();
  applyDocument(lang);
  void i18n.use(initReactI18next).init({
    resources,
    lng: lang,
    fallbackLng: "ar",
    defaultNS: "common",
    interpolation: { escapeValue: false },
    returnNull: false,
  });
  i18n.on("languageChanged", (next) => {
    const value: Lang = next === "en" ? "en" : "ar";
    localStorage.setItem(STORAGE_KEY, value);
    applyDocument(value);
  });
  return i18n;
}

/** Picks the Arabic or English field of an API object: pick(product, "name", lang). */
export function pick<K extends string>(
  source: Record<`${K}_ar` | `${K}_en`, string>,
  key: K,
  lang: Lang,
): string {
  return source[`${key}_${lang}`];
}

/**
 * Picks an optional _ar/_en field (a tier note, a color name), falling back to the other
 * language when the manager left this one empty. Null when both are empty.
 */
export function pickOptional<K extends string>(
  source: Record<`${K}_ar` | `${K}_en`, string | null | undefined>,
  key: K,
  lang: Lang,
): string | null {
  const other: Lang = lang === "ar" ? "en" : "ar";
  return source[`${key}_${lang}`] || source[`${key}_${other}`] || null;
}
