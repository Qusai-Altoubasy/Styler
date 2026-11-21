import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { api, unwrap, unwrapEmpty } from "@styler/shared/api/client";
import { isSessionEnded } from "./errors";

const SESSION_KEY = ["session"] as const;

/** The session, or null when logged out (the dashboard then shows the login page). */
export function useSession() {
  return useQuery({
    queryKey: SESSION_KEY,
    queryFn: async () => {
      try {
        return unwrap(await api.GET("/api/admin/session"));
      } catch (error) {
        if (isSessionEnded(error)) return null;
        throw error;
      }
    },
    staleTime: Infinity,
    retry: false,
  });
}

/** Back to the login page: forgets every loaded list, so nothing stays on screen. */
export function endSession(queryClient: QueryClient) {
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== SESSION_KEY[0] });
  queryClient.setQueryData(SESSION_KEY, null);
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (password: string) =>
      unwrapEmpty(await api.POST("/api/admin/login", { body: { password } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SESSION_KEY }),
  });
}

/** Logs out every device, this one included. */
export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => unwrapEmpty(await api.POST("/api/admin/logout")),
    onSuccess: () => endSession(queryClient),
  });
}

/** Every other device is logged out; this one gets a fresh session from the server. */
export function useChangePassword() {
  return useMutation({
    mutationFn: async (body: { current_password: string; new_password: string }) =>
      unwrapEmpty(await api.POST("/api/admin/password", { body })),
  });
}
