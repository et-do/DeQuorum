import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useRoles } from "@/lib/roles";

/**
 * /app layout. Renders the sidebar shell. Redirects to /onboarding if the
 * user hasn't picked any roles yet (i.e., never completed onboarding).
 *
 * The redirect runs both as a route `beforeLoad` (handles direct URLs)
 * and as a `useEffect` (handles client-side role clears). The duplicate
 * guard makes the unauthed state truly unreachable without rebuilding
 * /app on every render.
 */
export const Route = createFileRoute("/app")({
	beforeLoad: () => {
		// Storage isn't available during SSR; defer to client guard.
		if (typeof window === "undefined") return;
		try {
			const raw = window.localStorage.getItem("dequorum.roles");
			if (!raw) throw redirect({ to: "/onboarding" });
			const parsed = JSON.parse(raw);
			if (!Array.isArray(parsed) || parsed.length === 0) {
				throw redirect({ to: "/onboarding" });
			}
		} catch (e) {
			// `throw redirect(...)` above is what we want to re-raise; anything
			// else (JSON parse failures) also routes to onboarding.
			if (e instanceof Error && e.name === "RedirectError") throw e;
			throw redirect({ to: "/onboarding" });
		}
	},
	component: AppLayout,
});

function AppLayout() {
	const { roles, ready } = useRoles();

	useEffect(() => {
		if (ready && roles.size === 0) {
			window.location.assign("/onboarding");
		}
	}, [ready, roles]);

	if (!ready) return null;

	return (
		<AppShell>
			<Outlet />
		</AppShell>
	);
}
