import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["shared/**/*.test.ts", "storefront/src/**/*.test.ts", "admin/src/**/*.test.ts"],
  },
});
