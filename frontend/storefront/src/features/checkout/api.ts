import { useMutation } from "@tanstack/react-query";
import { api, unwrap } from "@styler/shared/api/client";
import type { OrderCreate } from "@styler/shared/api/types";

export function useCreateOrder() {
  return useMutation({
    mutationFn: async (body: OrderCreate) => unwrap(await api.POST("/api/orders", { body })),
  });
}
