import { toAsciiDigits } from "./digits";

/** Jordanian mobile numbers, normalized the same way as the backend (app/shared/phone.py). */

export const JORDAN_MOBILE = /^07[789][0-9]{7}$/;

/** "٠٧٩ ١٢٣-٤٥٦٧" -> "0791234567": ASCII digits, no spaces or dashes. */
export function normalizePhone(typed: string): string {
  return toAsciiDigits(typed).replace(/[\s-]/g, "");
}

export function isJordanMobile(typed: string): boolean {
  return JORDAN_MOBILE.test(normalizePhone(typed));
}

/** 07XXXXXXXX -> 9627XXXXXXXX, the form wa.me links need. */
export function toInternational(local: string): string {
  return "962" + normalizePhone(local).replace(/^0/, "");
}

/** 0791234567 -> "079 123 4567", easier to read back. */
export function formatPhone(local: string): string {
  const digits = normalizePhone(local);
  return digits.length === 10
    ? `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6)}`
    : local;
}
