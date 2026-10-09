import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In local mode the API runs on :8000; the dev server proxies /v1 to it.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/v1": "http://localhost:8000" },
  },
  build: { target: "es2022", sourcemap: false },
});
