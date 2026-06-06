/**
 * Ambient declarations for non-code assets imported for their side effects.
 * Same rationale as `env.d.ts`: we can't rely on `vite/client` (the host
 * devcontainer has no node_modules), and TypeScript 6 errors on side-effect
 * imports of modules without type declarations (TS2882). Declaring the
 * wildcard keeps `import "./foo.css"` / `import "pkg/dist/x.css"` type-clean.
 */

declare module "*.css";
