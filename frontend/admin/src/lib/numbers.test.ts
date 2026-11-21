import { describe, expect, it } from "vitest";
import { parseCount, parseId, parseMoney } from "./numbers";

describe("parseMoney", () => {
  it("reads Arabic digits and decimal separators", () => {
    expect(parseMoney("٧٫٥")).toBe("7.5");
    expect(parseMoney("2,25")).toBe("2.25");
    expect(parseMoney(" 10 ")).toBe("10");
    expect(parseMoney("007")).toBe("7");
    expect(parseMoney("0.5")).toBe("0.5");
    expect(parseMoney("2.50")).toBe("2.5");
    expect(parseMoney("3.000")).toBe("3");
    expect(parseMoney("0")).toBe("0");
  });
  it("refuses what the API would refuse", () => {
    expect(parseMoney("")).toBeNull();
    expect(parseMoney("-1")).toBeNull();
    expect(parseMoney("1.2345")).toBeNull();
    expect(parseMoney("abc")).toBeNull();
    expect(parseMoney("10000000")).toBeNull();
  });
});

describe("parseCount", () => {
  it("reads whole numbers from 1", () => {
    expect(parseCount("٢٥٠")).toBe(250);
    expect(parseCount("1")).toBe(1);
  });
  it("refuses zero, decimals and overflow", () => {
    expect(parseCount("0")).toBeNull();
    expect(parseCount("2.5")).toBeNull();
    expect(parseCount("")).toBeNull();
    expect(parseCount("3000000000")).toBeNull();
  });
});

describe("parseId", () => {
  it("reads ids from the address, refusing anything the API would", () => {
    expect(parseId("1005")).toBe(1005);
    expect(parseId("10o5")).toBeNull();
    expect(parseId("0")).toBeNull();
    expect(parseId("99999999999")).toBeNull();
    expect(parseId(undefined)).toBeNull();
  });
});
