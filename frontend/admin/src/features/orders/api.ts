import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api, unwrap, unwrapEmpty } from "@styler/shared/api/client";
import { nextOffset, PAGE_SIZE } from "../../lib/paging";
import type { MarkFilter, OrderUpdate } from "@styler/shared/api/types";

export function useOrderStats() {
  return useQuery({
    queryKey: ["orders", "stats"],
    queryFn: async () => unwrap(await api.GET("/api/admin/orders/stats")),
  });
}

/** Newest first, a page at a time; searched by name, phone or order number. */
export function useOrders(status: MarkFilter, q: string) {
  return useInfiniteQuery({
    queryKey: ["orders", "list", status, q],
    queryFn: async ({ pageParam }) =>
      unwrap(
        await api.GET("/api/admin/orders", {
          params: {
            query: { status, q: q.trim() || undefined, limit: PAGE_SIZE, offset: pageParam },
          },
        }),
      ),
    initialPageParam: 0,
    getNextPageParam: nextOffset,
    placeholderData: keepPreviousData,
    // New orders arrive while the dashboard is open.
    refetchInterval: 60_000,
  });
}

export function useOrder(orderId: number) {
  return useQuery({
    queryKey: ["order", orderId],
    queryFn: async () =>
      unwrap(
        await api.GET("/api/admin/orders/{order_id}", {
          params: { path: { order_id: orderId } },
        }),
      ),
  });
}

/** The mark, the internal note, or quote prices (the server then recomputes the totals). */
export function useUpdateOrder(orderId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: OrderUpdate) =>
      unwrap(
        await api.PATCH("/api/admin/orders/{order_id}", {
          params: { path: { order_id: orderId } },
          body,
        }),
      ),
    onSuccess: (order) => {
      queryClient.setQueryData(["order", orderId], order);
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}

export function useDeleteOrder(orderId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrapEmpty(
        await api.DELETE("/api/admin/orders/{order_id}", {
          params: { path: { order_id: orderId } },
        }),
      ),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["order", orderId] });
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}
