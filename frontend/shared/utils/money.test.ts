import { describe, expect, it } from "vitest";
import { formatMoney, fromFils, toFils, trimAmount } from "./money";

describe("money", () => {
  it("converts strings to fils and back without float drift", () => {
    expect(toFils("7.000")).toBe(7000);
    expect(toFils("0.1") + toFils("0.2")).toBe(300);
    expect(fromFils(300)).toBe("0.300");
    expect(fromFils(12345)).toBe("12.345");
  });

  it("trims trailing zeros for display", () => {
    expect(trimAmount("7.000")).toBe("7");
    expect(trimAmount("4.500")).toBe("4.5");
    expect(trimAmount("10")).toBe("10");
  });

  it("formats in both languages", () => {
    expect(formatMoney("7.000", "ar")).toBe("7 د.أ");
    expect(formatMoney(2500, "en")).toBe("2.5 JOD");
  });
});
