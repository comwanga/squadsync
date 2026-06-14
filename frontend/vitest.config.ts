import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    globals: true,
    // Vitest owns unit/component tests in tests/. Playwright owns e2e/ and runs
    // via `playwright test` — don't let vitest's default glob pull in *.spec.ts
    // from e2e/, where @playwright/test's test.describe() throws under vitest.
    include: ["tests/**/*.{test,spec}.{ts,tsx}"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
