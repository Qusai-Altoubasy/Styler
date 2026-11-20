import type { ProductSort } from "@styler/shared/api/types";
import type { ProductFilters } from "./api";

/** Filters live in the URL, so category cards link in and the back button works. */
const SORTS: ProductSort[] = ["default", "price_asc", "price_desc", "name"];

const PRICE = /^\d{1,7}(\.\d{1,3})?$/;

export function readFilters(params: URLSearchParams): ProductFilters {
  const category = Number(params.get("category"));
  const mode = params.get("mode");
  const sort = params.get("sort") as ProductSort | null;
  const price = (key: string) => {
    const value = params.get(key) ?? "";
    return PRICE.test(value) ? value : "";
  };
  return {
    categoryId: Number.isInteger(category) && category > 0 ? category : null,
    q: params.get("q") ?? "",
    minPrice: price("min"),
    maxPrice: price("max"),
    mode: mode === "fixed" || mode === "quote" ? mode : null,
    freeDelivery: params.get("free") === "1",
    sort: sort && SORTS.includes(sort) ? sort : "default",
  };
}

export function writeFilters(filters: ProductFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.categoryId) params.set("category", String(filters.categoryId));
  if (filters.q.trim()) params.set("q", filters.q);
  if (filters.minPrice) params.set("min", filters.minPrice);
  if (filters.maxPrice) params.set("max", filters.maxPrice);
  if (filters.mode) params.set("mode", filters.mode);
  if (filters.freeDelivery) params.set("free", "1");
  if (filters.sort !== "default") params.set("sort", filters.sort);
  return params;
}

export const isPrice = (value: string) => value === "" || PRICE.test(value);

/** Filters counted on the mobile "Filters" button (search and sort have their own controls). */
export function activeFilterCount(f: ProductFilters): number {
  return (
    Number(f.categoryId !== null) +
    Number(Boolean(f.minPrice || f.maxPrice)) +
    Number(f.mode !== null) +
    Number(f.freeDelivery)
  );
}
