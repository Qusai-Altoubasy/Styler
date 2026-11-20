import { describe, expect, it } from "vitest";
import { digitsOnly, toAsciiDecimal, toAsciiDigits } from "./digits";

describe("digits", () => {
  it("converts Arabic-Indic and Persian digits", () => {
    expect(toAsciiDigits("٢٠٠ و ۴۵")).toBe("200 و 45");
    expect(digitsOnly("١٢-٣ abc")).toBe("123");
  });

  it("reads the Arabic decimal separator and a comma as the decimal point", () => {
    expect(toAsciiDecimal("١٫٥")).toBe("1.5");
    expect(toAsciiDecimal("2,25")).toBe("2.25");
    expect(toAsciiDecimal("١٬٠٠٠")).toBe("1000");
  });
});
