/**
 * Frontend environment constants.
 *
 * `APP_PATH` is where the "Launch App" CTA navigates. It's a route inside
 * this SPA (the /app/* tree), not an external URL — same origin, same
 * frontend service, same theme.
 */

export const APP_PATH = "/app" as const;

export const SITE_NAME = "DeQuorum";

export const NAV_LINKS = [
	{ to: "/", label: "Home" },
	{ to: "/about", label: "About" },
	{ to: "/whitepaper", label: "Whitepaper" },
	{ to: "/docs", label: "Docs" },
	{ to: "/pricing", label: "Pricing" },
] as const;
