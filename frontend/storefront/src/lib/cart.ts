import { useSyncExternalStore } from "react";
import type { PriceTier, PricingMode, ProductColor } from "@styler/shared/api/types";

/**
 * The cart lives in localStorage. Each line holds the customer's choices (what the
 * order request sends) plus a snapshot for display. Prices here are for display only:
 * the server recalculates every order.
 */
export interface CartLine {
  key: string;
  productId: number;
  tierId: number | null;
  colorId: number | null;
  approxQuantity: number | null;
  itemCount: number;
  snapshot: {
    name_ar: string;
    name_en: string;
    image_url: string | null;
    pricing_mode: PricingMode;
    free_delivery: boolean;
    tier: PriceTier | null;
    color: ProductColor | null;
  };
}

/** The API's caps: 50 lines per order and 10,000 items per line. */
export const MAX_LINES = 50;
export const MAX_ITEM_COUNT = 10_000;

const STORAGE_KEY = "styler.cart.v1";
const listeners = new Set<() => void>();
let lines: CartLine[] = load();

function load(): CartLine[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed) ? (parsed as CartLine[]).filter((l) => l && l.key) : [];
  } catch {
    return [];
  }
}

function commit(next: CartLine[]) {
  lines = next;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(lines));
  listeners.forEach((listener) => listener());
}

// Another tab changed the cart.
window.addEventListener("storage", (event) => {
  if (event.key !== STORAGE_KEY) return;
  lines = load();
  listeners.forEach((listener) => listener());
});

export function lineKey(l: Pick<CartLine, "productId" | "tierId" | "colorId" | "approxQuantity">) {
  return [l.productId, l.tierId ?? "-", l.colorId ?? "-", l.approxQuantity ?? "-"].join(":");
}

const clampCount = (n: number) => Math.min(MAX_ITEM_COUNT, Math.max(1, Math.round(n) || 1));

/** Adds a line, or adds to the count of the same choice. False when the cart is full. */
export function addToCart(line: Omit<CartLine, "key">): boolean {
  const key = lineKey(line);
  const existing = lines.find((l) => l.key === key);
  if (existing) {
    commit(
      lines.map((l) =>
        l.key === key
          ? { ...l, snapshot: line.snapshot, itemCount: clampCount(l.itemCount + line.itemCount) }
          : l,
      ),
    );
    return true;
  }
  if (lines.length >= MAX_LINES) return false;
  commit([...lines, { ...line, key, itemCount: clampCount(line.itemCount) }]);
  return true;
}

export function setItemCount(key: string, count: number) {
  commit(lines.map((l) => (l.key === key ? { ...l, itemCount: clampCount(count) } : l)));
}

export function removeLine(key: string) {
  commit(lines.filter((l) => l.key !== key));
}

export function clearCart() {
  commit([]);
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useCart(): CartLine[] {
  return useSyncExternalStore(subscribe, () => lines);
}

export function useCartCount(): number {
  return useSyncExternalStore(subscribe, () => lines.reduce((sum, l) => sum + l.itemCount, 0));
}
