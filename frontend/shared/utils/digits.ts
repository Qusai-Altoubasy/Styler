/** Arabic-Indic and Persian digits, the default on many Arabic phone keyboards. */
const LOCAL_DIGITS = "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹";

/** "٢٠٠" -> "200": every typed number goes through this before it is checked. */
export function toAsciiDigits(text: string): string {
  return [...text]
    .map((ch) => {
      const index = LOCAL_DIGITS.indexOf(ch);
      return index === -1 ? ch : String(index % 10);
    })
    .join("");
}

/** Keeps the digits of what was typed, in ASCII. */
export function digitsOnly(text: string): string {
  return toAsciiDigits(text).replace(/\D/g, "");
}

/**
 * A typed decimal number in ASCII: Arabic-Indic digits, and the Arabic decimal
 * separator (٫) or a comma as the decimal point. Arabic thousands separators (٬) go.
 * "١٫٥" -> "1.5", "2,25" -> "2.25".
 */
export function toAsciiDecimal(text: string): string {
  return toAsciiDigits(text).replace(/[٫,]/g, ".").replace(/٬/g, "");
}
