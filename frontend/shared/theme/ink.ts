import type { BrandColor } from "../api/types";

/**
 * A logo ink as a theme color: `var(--cyan)` and so on. Black prints as `--key`, the
 * theme's own ink, so it stays visible on the dark theme's black paper. Both apps use
 * this one rule for category colors.
 */
export function inkVar(color: BrandColor): string {
  return `var(--${color === "black" ? "key" : color})`;
}
