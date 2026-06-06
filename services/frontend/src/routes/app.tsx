import { createFileRoute, Outlet } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth";
import { useRoles } from "@/lib/roles";

export const Route = createFileRoute("/app")({
	component: AppLayout,
});

function AppLayout() {
	const { user, ready: authReady } = useAuth();
	const { roles, ready: rolesReady } = useRoles();

	// Guard 1: not signed in → /signin
	useEffect(() => {
		if (authReady && !user) {
			window.location.assign("/signin");
		}
	}, [authReady, user]);

	// Guard 2: signed in but no roles → /onboarding
	useEffect(() => {
		if (authReady && user && rolesReady && roles.size === 0) {
			window.location.assign("/onboarding");
		}
	}, [authReady, user, rolesReady, roles]);

	if (!authReady || !rolesReady) return null;
	if (!user) return null;

	return (
		<AppShell>
			<Outlet />
		</AppShell>
	);
}
