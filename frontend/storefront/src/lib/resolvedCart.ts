import { useQueries } from "@tanstack/react-query";
import { api, ApiError, unwrap } from "@styler/shared/api/client";
import type { PriceTier, ProductColor, ProductDetail } from "@styler/shared/api/types";
import type { CartLine } from "./cart";
import type { TotalsLine } from "./totals";

export type LineStatus = "ok" | "loading" | "unavailable";

export interface ResolvedLine {
  line: CartLine;
  status: LineStatus;
  /** Current product data when loaded, else the snapshot saved when it was added. */
  name_ar: string;
  name_en: string;
  image_url: string | null;
  categoryId: number | null;
  tier: PriceTier | null;
  color: ProductColor | null;
  totals: TotalsLine;
}

/**
 * Checks each cart line against the product as it is now: a hidden or deleted product,
 * a removed quantity or color, or a changed pricing mode makes the line unavailable.
 */
export function resolveLine(
  line: CartLine,
  product: ProductDetail | null | undefined,
): ResolvedLine {
  const snap = line.snapshot;
  if (product === undefined) {
    return {
      line,
      status: "loading",
      ...pickNames(snap),
      categoryId: null,
      tier: snap.tier,
      color: snap.color,
      totals: totalsLine(line, snap.pricing_mode, snap.tier, snap.free_delivery),
    };
  }
  const tier = product?.price_tiers.find((x) => x.id === line.tierId) ?? null;
  const color = product?.colors.find((c) => c.id === line.colorId) ?? null;
  const ok =
    product !== null &&
    product.pricing_mode === snap.pricing_mode &&
    (product.pricing_mode === "quote" ? line.tierId === null : tier !== null) &&
    (product.colors.length === 0 ? line.colorId === null : color !== null);

  if (!ok || !product) {
    return {
      line,
      status: "unavailable",
      ...pickNames(product ?? snap),
      categoryId: product?.category.id ?? null,
      tier: snap.tier,
      color: snap.color,
      totals: { ...totalsLine(line, snap.pricing_mode, null, false), unitPrice: null },
    };
  }
  return {
    line,
    status: "ok",
    ...pickNames(product),
    categoryId: product.category.id,
    tier,
    color,
    totals: totalsLine(line, product.pricing_mode, tier, product.free_delivery),
  };
}

function pickNames(source: { name_ar: string; name_en: string; image_url: string | null }) {
  return { name_ar: source.name_ar, name_en: source.name_en, image_url: source.image_url };
}

function totalsLine(
  line: CartLine,
  mode: "fixed" | "quote",
  tier: PriceTier | null,
  freeDelivery: boolean,
): TotalsLine {
  return {
    itemCount: line.itemCount,
    pricingMode: mode,
    unitPrice: mode === "fixed" ? (tier?.price ?? null) : null,
    freeDelivery,
  };
}

/** The cart lines with fresh product data; unavailable lines are left out of totals. */
export function useResolvedCart(lines: CartLine[]) {
  const ids = [...new Set(lines.map((l) => l.productId))];
  const results = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["product", id],
      queryFn: async () =>
        unwrap(
          await api.GET("/api/products/{product_id}", { params: { path: { product_id: id } } }),
        ),
      retry: (count: number, error: Error) =>
        !(error instanceof ApiError && error.status === 404) && count < 1,
    })),
  });

  const byId = new Map<number, ProductDetail | null | undefined>();
  ids.forEach((id, i) => {
    const r = results[i];
    if (r?.data) byId.set(id, r.data);
    else if (r?.error instanceof ApiError && r.error.status === 404) byId.set(id, null);
    else byId.set(id, undefined);
  });

  const resolved = lines.map((l) => resolveLine(l, byId.get(l.productId)));
  return {
    resolved,
    hasUnavailable: resolved.some((r) => r.status === "unavailable"),
    totalsLines: resolved.filter((r) => r.status !== "unavailable").map((r) => r.totals),
  };
}
