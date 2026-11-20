import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@styler/shared/api/client";
import type { Lang } from "@styler/shared/i18n/setup";
import type { PricingMode, ProductSort } from "@styler/shared/api/types";

export interface ProductFilters {
  categoryId: number | null;
  q: string;
  minPrice: string;
  maxPrice: string;
  mode: PricingMode | null;
  freeDelivery: boolean;
  sort: ProductSort;
}

export function useProducts(filters: ProductFilters, lang: Lang) {
  return useQuery({
    queryKey: ["products", filters, lang],
    queryFn: async () =>
      unwrap(
        await api.GET("/api/products", {
          params: {
            query: {
              category_id: filters.categoryId ?? undefined,
              q: filters.q.trim() || undefined,
              min_price: filters.minPrice || undefined,
              max_price: filters.maxPrice || undefined,
              pricing_mode: filters.mode ?? undefined,
              free_delivery: filters.freeDelivery || undefined,
              sort: filters.sort,
              lang,
            },
          },
        }),
      ),
    // Keep the current grid on screen while the next filter result loads.
    placeholderData: keepPreviousData,
  });
}
