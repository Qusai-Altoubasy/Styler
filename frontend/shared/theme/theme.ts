import { useCallback, useSyncExternalStore } from "react";

/** The customer's choice; "system" follows the device setting. */
export type ThemeChoice = "system" | "light" | "dark";
export type Theme = "light" | "dark";

const STORAGE_KEY = "styler.theme";
const media = () => window.matchMedia("(prefers-color-scheme: dark)");
const listeners = new Set<() => void>();

function readChoice(): ThemeChoice {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved === "light" || saved === "dark" ? saved : "system";
}

function resolve(choice: ThemeChoice): Theme {
  if (choice !== "system") return choice;
  return media().matches ? "dark" : "light";
}

function apply() {
  document.documentElement.dataset.theme = resolve(readChoice());
  listeners.forEach((listener) => listener());
}

/** Call once at startup: applies the theme and follows device changes. */
export function initTheme() {
  apply();
  media().addEventListener("change", apply);
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, () => resolve(readChoice()));
  const toggle = useCallback(() => {
    const next: Theme = resolve(readChoice()) === "dark" ? "light" : "dark";
    // Back to "system" when the choice matches the device, so it keeps following it.
    if (next === resolve("system")) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, next);
    apply();
  }, []);
  return { theme, toggle };
}
