import { defineConfig } from "vitest/config";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  server: {
    host: true,
    port: 5173
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
    pool: "forks",
    poolOptions: {
      forks: {
        singleFork: true
      }
    },
    fileParallelism: false,
    clearMocks: true,
    restoreMocks: true,
    unstubGlobals: true,
    testTimeout: 20_000,
    hookTimeout: 20_000,
    teardownTimeout: 10_000
  }
});
