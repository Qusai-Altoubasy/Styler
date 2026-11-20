import { describe, expect, it } from "vitest";
import { computeTotals, type TotalsLine } from "./totals";

const settings = {
  governorates: [
    { governorate: "amman" as const, zone: "a" as const, delivery_fee: "2.000" },
    { governorate: "irbid" as const, zone: "b" as const, delivery_fee: "3.000" },
  ],
};
const fixed = (price: string, count = 1, free = false): TotalsLine => ({
  itemCount: count,
  pricingMode: "fixed",
  unitPrice: price,
  freeDelivery: free,
});
const quote: TotalsLine = {
  itemCount: 1,
  pricingMode: "quote",
  unitPrice: null,
  freeDelivery: false,
};

describe("computeTotals", () => {
  it("adds fixed lines and the zone's delivery", () => {
    const t = computeTotals([fixed("7.000", 2), fixed("0.350", 3)], settings, "irbid");
    expect(t.subtotal).toBe(15_050);
    expect(t.delivery).toBe(3000);
    expect(t.total).toBe(18_050);
    expect(t.awaitingQuote).toBe(false);
  });

  it("leaves quote lines out of a mixed order and flags them", () => {
    const t = computeTotals([fixed("5.000"), quote], settings, "amman");
    expect(t.total).toBe(7000);
    expect(t.awaitingQuote).toBe(true);
  });

  it("frees delivery for the whole order when one product has free delivery", () => {
    const t = computeTotals([fixed("5.000"), fixed("8.000", 1, true)], settings, "irbid");
    expect(t.delivery).toBe(0);
    expect(t.total).toBe(13_000);
  });

  it("has no delivery until a governorate is chosen", () => {
    expect(computeTotals([fixed("5.000")], settings, null).delivery).toBeNull();
  });
});
