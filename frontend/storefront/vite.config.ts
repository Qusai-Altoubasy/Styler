import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// Proxy targets come from storefront/.env (see .env.example); there are no defaults,
// so a missing value stops the dev server instead of guessing.
function required(env: Record<string, string>, name: string): string {
  const value = env[name];
  if (!value) throw new Error(`${name} is not set: copy storefront/.env.example to .env`);
  return value;
}

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, import.meta.dirname, "");
  const serving = command === "serve";
  return {
    plugins: [react()],
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
