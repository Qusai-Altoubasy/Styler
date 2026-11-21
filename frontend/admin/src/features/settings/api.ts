import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@styler/shared/api/client";
import type { SettingsUpdate } from "@styler/shared/api/types";

export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: async () => unwrap(await api.GET("/api/admin/settings")),
  });
}

export function useSaveSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: SettingsUpdate) =>
      unwrap(await api.PATCH("/api/admin/settings", { body })),
    onSuccess: (saved) => queryClient.setQueryData(["settings"], saved),
  });
}
