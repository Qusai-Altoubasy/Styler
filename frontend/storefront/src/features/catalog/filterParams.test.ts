import { describe, expect, it } from "vitest";
import { activeFilterCount, readFilters, writeFilters } from "./filterParams";

describe("filter params", () => {
  it("round-trips through the URL", () => {
    const params = new URLSearchParams(
      "category=3&q=mug&min=2&max=10.5&mode=fixed&free=1&sort=price_asc",
    );
    const filters = readFilters(params);
    expect(filters).toEqual({
      categoryId: 3,
      q: "mug",
      minPrice: "2",
      maxPrice: "10.5",
      mode: "fixed",
      freeDelivery: true,
      sort: "price_asc",
    });
    expect(writeFilters(filters).toString()).toBe(params.toString());
    expect(activeFilterCount(filters)).toBe(4);
  });

  it("ignores values the API would refuse", () => {
    const filters = readFilters(new URLSearchParams("category=x&min=-1&mode=free&sort=random"));
    expect(filters.categoryId).toBeNull();
    expect(filters.minPrice).toBe("");
    expect(filters.mode).toBeNull();
    expect(filters.sort).toBe("default");
  });
});
