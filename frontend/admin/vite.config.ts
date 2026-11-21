import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// Proxy targets come from admin/.env (see .env.example); there are no defaults,
// so a missing value stops the dev server instead of guessing.
function required(env: Record<string, string>, name: string): string {
  const value = env[name];
  if (!value) throw new Error(`${name} is not set: copy admin/.env.example to .env`);
  return value;
}

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, import.meta.dirname, "");
  const serving = command === "serve";
  return {
    plugins: [react()],
    // The WebP encoder for browsers without one (Safari) is WebAssembly, loaded on demand.
    optimizeDeps: { exclude: ["@jsquash/webp"] },
    server: serving
      ? {
          // The storefront uses 5173. MinIO's upload CORS allows this origin
          // (MINIO_API_CORS_ALLOW_ORIGIN in deploy/.env.dev).
          port: 5174,
          strictPort: true,
          proxy: {
            "/api": required(env, "API_PROXY_TARGET"),
            "/media": { target: required(env, "MEDIA_PROXY_TARGET"), changeOrigin: true },
          },
        }
      : undefined,
  };
});
