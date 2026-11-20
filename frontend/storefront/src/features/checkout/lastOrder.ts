import type { OrderConfirmation } from "@styler/shared/api/types";

/**
 * The last confirmation, kept so the "we got your order" page survives a refresh or a
 * return from WhatsApp. There is no public endpoint to read an order back.
 *
 * sessionStorage, not localStorage: it holds the customer's name, phone and address,
 * so it lives only as long as the tab. A trip to WhatsApp and back keeps the tab; on a
 * shared phone the next person never finds it.
 */
const STORAGE_KEY = "styler.lastOrder";

export function saveLastOrder(order: OrderConfirmation) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(order));
}

export function readLastOrder(id: number): OrderConfirmation | null {
  try {
    const order = JSON.parse(
      sessionStorage.getItem(STORAGE_KEY) ?? "null",
    ) as OrderConfirmation | null;
    return order && order.id === id ? order : null;
  } catch {
    return null;
  }
}
