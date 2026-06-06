/**
 * Local typings for Vite's `import.meta.env`. We can't rely on `vite/client`
 * via `tsconfig.types` because the host devcontainer doesn't have
 * node_modules; declaring the surface we use keeps tsc happy in CI and
 * IDE without that dep.
 */

interface ImportMetaEnv {
	readonly VITE_PROXY_API_TARGET?: string;
	readonly VITE_FIREBASE_API_KEY?: string;
	readonly VITE_FIREBASE_AUTH_DOMAIN?: string;
	readonly VITE_FIREBASE_PROJECT_ID?: string;
	readonly MODE?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
