import "@fontsource-variable/readex-pro";
import "@fontsource/ibm-plex-sans-arabic/400.css";
import "@fontsource/ibm-plex-sans-arabic/500.css";
import "@fontsource/ibm-plex-sans-arabic/600.css";
import "@styler/shared/theme/theme.css";
import "@styler/shared/ui/ui.css";
import "./ui/admin.css";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import { initTheme } from "@styler/shared/theme/theme";
import "./app/i18n";
import { router } from "./app/router";
import { isRetryable, isSessionEnded } from "./lib/errors";
import { endSession } from "./lib/session";

initTheme();

// Any request that finds the session gone (logged out on another device, expired, or the
// password changed elsewhere) sends the dashboard back to the login page.
const onError = (error: unknown) => {
  if (isSessionEnded(error)) endSession(queryClient);
};

const queryClient: QueryClient = new QueryClient({
  queryCache: new QueryCache({ onError }),
  mutationCache: new MutationCache({ onError }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Once, and only for a lost connection or a server error: a 404 or 422 will not
      // change on a second try.
      retry: (count, error) => count < 1 && isRetryable(error),
    },
  },
});

const root = document.getElementById("root");
if (!root) throw new Error("index.html has no #root element");

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
