import { describe, expect, it } from "vitest";
import type { ProductDetail } from "@styler/shared/api/types";
import type { CartLine } from "./cart";
import { resolveLine } from "./resolvedCart";

const tier = { id: 5, quantity: 250, price: "7.000", note_ar: null, note_en: null };
const color = { id: 9, name_ar: "أسود", name_en: "Black", hex: "#000000" };
const product: ProductDetail = {
  id: 1,
  category: { id: 2, name_ar: "س", name_en: "S" },
  name_ar: "ستيكر",
  name_en: "Sticker",
  description_ar: "",
  description_en: "",
  image_url: null,
  pricing_mode: "fixed",
  free_delivery: false,
  price: "7.000",
  price_tiers: [{ ...tier, price: "6.500" }],
  colors: [color],
};
const line: CartLine = {
  key: "1:5:9:-",
  productId: 1,
  tierId: 5,
  colorId: 9,
  approxQuantity: null,
  itemCount: 2,
  snapshot: {
    name_ar: "ستيكر",
    name_en: "Sticker",
    image_url: null,
    pricing_mode: "fixed",
    free_delivery: false,
    tier,
    color,
  },
};

describe("resolveLine", () => {
  it("uses the current price, not the one saved in the cart", () => {
    const r = resolveLine(line, product);
    expect(r.status).toBe("ok");
    expect(r.totals.unitPrice).toBe("6.500");
  });

  it("marks a deleted product, a removed tier or a removed color unavailable", () => {
    expect(resolveLine(line, null).status).toBe("unavailable");
    expect(resolveLine(line, { ...product, price_tiers: [] }).status).toBe("unavailable");
    expect(resolveLine(line, { ...product, colors: [{ ...color, id: 10 }] }).status).toBe(
      "unavailable",
    );
  });

  it("marks a product that switched to quote pricing unavailable", () => {
    expect(resolveLine(line, { ...product, pricing_mode: "quote" }).status).toBe("unavailable");
  });

  it("shows the snapshot while loading", () => {
    const r = resolveLine(line, undefined);
    expect(r.status).toBe("loading");
    expect(r.totals.unitPrice).toBe("7.000");
  });
});
