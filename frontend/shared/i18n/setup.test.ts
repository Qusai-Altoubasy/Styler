import { describe, expect, it } from "vitest";
import { pickOptional } from "./setup";

describe("pickOptional", () => {
  const tier = { note_ar: "4 سم", note_en: null };

  it("uses the page language, falling back to the other one", () => {
    expect(pickOptional(tier, "note", "ar")).toBe("4 سم");
    expect(pickOptional(tier, "note", "en")).toBe("4 سم");
    expect(pickOptional({ note_ar: "", note_en: "4 cm" }, "note", "ar")).toBe("4 cm");
  });

  it("is null when both are empty", () => {
    expect(pickOptional({ note_ar: null, note_en: "" }, "note", "en")).toBeNull();
  });
});
