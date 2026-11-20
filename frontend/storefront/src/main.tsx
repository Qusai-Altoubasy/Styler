import "@fontsource-variable/readex-pro";
import "@fontsource/ibm-plex-sans-arabic/400.css";
import "@fontsource/ibm-plex-sans-arabic/500.css";
import "@fontsource/ibm-plex-sans-arabic/600.css";
import "@styler/shared/theme/theme.css";
import "./ui/ui.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LazyMotion, MotionConfig } from "motion/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import { initTheme } from "@styler/shared/theme/theme";
import "./app/i18n";
import { router } from "./app/router";

initTheme();

const loadMotionFeatures = () => import("./lib/motionFeatures").then((mod) => mod.default);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 60_000, retry: 1, refetchOnWindowFocus: false },
  },
});

const root = document.getElementById("root");
if (!root) throw new Error("index.html has no #root element");

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      {/* Follows the device's reduced-motion setting for every animation. */}
      <MotionConfig reducedMotion="user">
        {/* The engine loads in its own chunk; `strict` refuses a full `motion.` import. */}
        <LazyMotion features={loadMotionFeatures} strict>
          <RouterProvider router={router} />
        </LazyMotion>
      </MotionConfig>
    </QueryClientProvider>
  </StrictMode>,
);
