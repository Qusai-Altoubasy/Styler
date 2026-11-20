import type { Governorate, PublicSettings } from "@styler/shared/api/types";
import { toFils } from "@styler/shared/utils/money";

export interface TotalsLine {
  itemCount: number;
  pricingMode: "fixed" | "quote";
  /** The tier price for fixed lines; null for quote lines. */
  unitPrice: string | null;
  freeDelivery: boolean;
}

export interface Totals {
  subtotal: number; // fils
  /** Null until a governorate is chosen. */
  delivery: number | null;
  total: number;
  freeDelivery: boolean;
  awaitingQuote: boolean;
}

/**
 * The same rules as the server (orders/pricing.py), for display only: priced lines add
 * up, quote lines wait for a price, and one free-delivery product frees the whole order.
 */
export function computeTotals(
  lines: TotalsLine[],
  settings: Pick<PublicSettings, "governorates"> | undefined,
  governorate: Governorate | null,
): Totals {
  let subtotal = 0;
  for (const line of lines) {
    if (line.pricingMode === "fixed" && line.unitPrice !== null) {
      subtotal += toFils(line.unitPrice) * line.itemCount;
    }
  }
  const freeDelivery = lines.some((l) => l.freeDelivery);
  const zone = settings?.governorates.find((g) => g.governorate === governorate);
  const delivery = freeDelivery ? 0 : zone ? toFils(zone.delivery_fee) : null;
  return {
    subtotal,
    delivery,
    total: subtotal + (delivery ?? 0),
    freeDelivery,
    awaitingQuote: lines.some((l) => l.pricingMode === "quote"),
  };
}
