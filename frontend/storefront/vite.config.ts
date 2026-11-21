import { execFileSync } from "node:child_process";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// Proxy targets come from storefront/.env (see .env.example); there are no defaults,
// so a missing value stops the dev server instead of guessing.
function required(env: Record<string, string>, name: string): string {
  const value = env[name];
  if (!value) throw new Error(`${name} is not set: copy storefront/.env.example to .env`);
  return value;
}

/**
 * The commit the app was built from, shown (in the background color) under the footer's
 * copyright: select the text to read it. The same hash tags the backend image on deploy.
 */
function commitHash(): string {
  try {
    return execFileSync("git", ["rev-parse", "--short", "HEAD"], { encoding: "utf8" }).trim();
  } catch {
    return "unknown";
  }
}

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, import.meta.dirname, "");
  const serving = command === "serve";
  return {
    plugins: [react()],
    define: { __APP_VERSION__: JSON.stringify(commitHash()) },
    server: serving
      ? {
          proxy: {
            "/api": required(env, "API_PROXY_TARGET"),
            "/media": { target: required(env, "MEDIA_PROXY_TARGET"), changeOrigin: true },
          },
        }
      : undefined,
  };
});
