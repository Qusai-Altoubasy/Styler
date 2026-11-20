import { useQuery } from "@tanstack/react-query";
import { api, ApiError, unwrap } from "@styler/shared/api/client";

export function useProduct(productId: number) {
  return useQuery({
    queryKey: ["product", productId],
    queryFn: async () =>
      unwrap(
        await api.GET("/api/products/{product_id}", {
          params: { path: { product_id: productId } },
        }),
      ),
    enabled: Number.isInteger(productId) && productId > 0,
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
