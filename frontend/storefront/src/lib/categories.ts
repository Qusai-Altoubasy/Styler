import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@styler/shared/api/client";
import type { BrandColor } from "@styler/shared/api/types";
import { inkFor } from "../ui/ink";

/** Visible categories; also used to give a product image its category's ink. */
export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: async () => unwrap(await api.GET("/api/categories")),
  });
}

/** The ink of a category by id, falling back to a stable one while loading. */
export function useCategoryInk(): (categoryId: number) => BrandColor {
  const { data } = useCategories();
  return (categoryId) => data?.find((c) => c.id === categoryId)?.color ?? inkFor(categoryId);
}
