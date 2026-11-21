import { describe, expect, it } from "vitest";
import { nextOffset } from "./paging";

describe("nextOffset", () => {
  it("continues after the rows loaded so far", () => {
    expect(nextOffset({ items: [1, 2], total: 5, offset: 0 })).toBe(2);
  });
  it("stops at the end, and on an empty page even if the total says more", () => {
    expect(nextOffset({ items: [1, 2], total: 4, offset: 2 })).toBeUndefined();
    expect(nextOffset({ items: [], total: 9, offset: 50 })).toBeUndefined();
  });
});
