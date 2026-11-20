/**
 * Money arrives from the API as strings with 3 decimals ("7.000", 1 JOD = 1000 fils).
 * Arithmetic is done in integer fils so totals never drift like floats do.
 */

export function toFils(amount: string): number {
  const match = /^(-?)(\d+)(?:\.(\d{1,3}))?$/.exec(amount.trim());
  if (!match) throw new Error(`not a money amount: ${amount}`);
  const [, sign, whole, fraction = ""] = match;
  const fils = Number(whole) * 1000 + Number(fraction.padEnd(3, "0"));
  return sign ? -fils : fils;
}

export function fromFils(fils: number): string {
  const sign = fils < 0 ? "-" : "";
  const abs = Math.abs(fils);
  return `${sign}${Math.floor(abs / 1000)}.${String(abs % 1000).padStart(3, "0")}`;
}

/** "7.000" -> "7", "4.500" -> "4.5", "0.250" -> "0.25". */
export function trimAmount(amount: string): string {
  return amount.includes(".") ? amount.replace(/\.?0+$/, "") : amount;
}

export function formatMoney(amount: string | number, lang: "ar" | "en"): string {
  const value = trimAmount(typeof amount === "number" ? fromFils(amount) : amount);
  return lang === "ar" ? `${value} د.أ` : `${value} JOD`;
}
