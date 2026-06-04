/// <reference types="vitest" />
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [
		// TanStack Router's vite plugin must come BEFORE @vitejs/plugin-react
		// so the generated routeTree.gen.ts is picked up by the React refresh
		// transform on the same run.
		TanStackRouterVite({
			target: "react",
			routesDirectory: "./src/routes",
			generatedRouteTree: "./src/routeTree.gen.ts",
			// autoCodeSplitting emits virtual module IDs that match route paths
			// (`/app`, `/about`, etc.). In our container the WORKDIR is `/app`,
			// so Vite tries to read the URL `/app` as if it were the literal
			// filesystem path /app and errors EISDIR. Bundles still tree-shake
			// fine without splitting; revisit if marketing+app share is a real
			// bundle-size issue.
			autoCodeSplitting: false,
		}),
		react(),
		tailwindcss(),
	],
	resolve: {
		alias: {
			"@": new URL("./src", import.meta.url).pathname,
		},
	},
	server: {
		host: "0.0.0.0",
		port: 5173,
		// When running outside the compose network (`npm run dev` directly),
		// proxy /api to the local app. Inside compose, Caddy handles this and
		// Vite doesn't need to know.
		proxy: {
			"/api": {
				target: process.env.VITE_PROXY_API_TARGET || "http://localhost:8000",
				changeOrigin: true,
			},
		},
	},
	test: {
		globals: true,
		environment: "jsdom",
		setupFiles: ["./src/test/setup.ts"],
		css: true,
	},
});
