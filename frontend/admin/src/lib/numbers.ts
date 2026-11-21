import { digitsOnly, toAsciiDecimal } from "@styler/shared/utils/digits";
import { trimAmount } from "@styler/shared/utils/money";

/** NUMERIC(10, 3): up to 9,999,999.999 JOD. */
const MAX_MONEY = 9_999_999.999;
/** Ids and quantities are int4 in the database. */
export const MAX_INT = 2_147_483_647;

/**
 * A typed price ("٧٫٥", "7,5", " 7 ") as the API's money string ("7.5"), or null when it
 * is not a valid amount: digits with up to 3 decimals, not negative, within the column.
 * Written the way saved amounts are shown ("2.50" -> "2.5", "007" -> "7"), so a typed
 * value can be compared with a saved one.
 */
export function parseMoney(typed: string): string | null {
  const text = toAsciiDecimal(typed).trim();
  if (!/^\d+(\.\d{1,3})?$/.test(text)) return null;
  if (Number(text) > MAX_MONEY) return null;
  return trimAmount(text.replace(/^0+(?=\d)/, ""));
}

/** A typed whole number of at least 1 ("٢٥٠" -> 250), or null. */
export function parseCount(typed: string): number | null {
  const text = toAsciiDecimal(typed).trim();
  if (!/^\d+$/.test(text)) return null;
  const value = Number(digitsOnly(text));
  return value >= 1 && value <= MAX_INT ? value : null;
}

/** An id from the address ("/orders/1005"), or null when it cannot be one (int4, from 1). */
export function parseId(text: string | undefined): number | null {
  if (!text || !/^\d+$/.test(text)) return null;
  const value = Number(text);
  return value >= 1 && value <= MAX_INT ? value : null;
}
