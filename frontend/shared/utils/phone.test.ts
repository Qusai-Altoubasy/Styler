import { describe, expect, it } from "vitest";
import { formatPhone, isJordanMobile, normalizePhone, toInternational } from "./phone";

describe("phone", () => {
  it("normalizes Arabic-Indic digits, spaces and dashes like the backend", () => {
    expect(normalizePhone("٠٧٩ ١٢٣-٤٥٦٧")).toBe("0791234567");
    expect(normalizePhone("۰۷۸ ۱۲۳ ۴۵۶۷")).toBe("0781234567");
  });

  it("accepts 077, 078 and 079 numbers only", () => {
    expect(isJordanMobile("0771234567")).toBe(true);
    expect(isJordanMobile("079-123-4567")).toBe(true);
    expect(isJordanMobile("0761234567")).toBe(false);
    expect(isJordanMobile("079123456")).toBe(false);
    expect(isJordanMobile("+962791234567")).toBe(false);
  });

  it("builds the international and readable forms", () => {
    expect(toInternational("0790087017")).toBe("962790087017");
    expect(formatPhone("0790087017")).toBe("079 008 7017");
  });
});
