import type { BrandColor } from "@styler/shared/api/types";

const INKS: BrandColor[] = ["cyan", "magenta", "yellow"];

/** Picks an ink for an item without an image or category color, stable per id. */
export function inkFor(id: number): BrandColor {
  return INKS[id % INKS.length] ?? "cyan";
}
