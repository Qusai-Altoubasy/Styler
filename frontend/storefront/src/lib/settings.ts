import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@styler/shared/api/client";

/** Delivery fees, governorates and contact links; used by the footer, cart and checkout. */
export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: async () => unwrap(await api.GET("/api/settings")),
    staleTime: 5 * 60_000,
  });
}
