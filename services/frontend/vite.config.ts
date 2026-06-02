import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // When running outside the compose network (`pnpm dev` directly), proxy
    // /api to the local app. Inside compose, Caddy handles this and Vite
    // doesn't need to know.
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
