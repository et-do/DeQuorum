import type { QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Outlet, useRouterState } from "@tanstack/react-router";
import { Footer } from "@/components/layout/Footer";
import { TopNav } from "@/components/layout/TopNav";
import { TopProgress } from "@/components/ui/TopProgress";

/**
 * Root layout. Marketing routes (everything outside /app/*) render with
 * the marketing TopNav + Footer; /app/* routes render bare (AppShell
 * provides its own sidebar chrome).
 *
 * Onboarding is treated like a marketing route — wizard chrome is
 * minimal; let the wizard own its own page space.
 */
export const Route = createRootRouteWithContext<{
	queryClient: QueryClient;
}>()({
	component: RootComponent,
});

function RootComponent() {
	const path = useRouterState({ select: (s) => s.location.pathname });
	const isApp = path === "/app" || path.startsWith("/app/");

	if (isApp) {
		return (
			<>
				<TopProgress />
				<Outlet />
			</>
		);
	}

	return (
		<div className="flex min-h-screen flex-col bg-bg text-fg">
			<TopProgress />
			<TopNav />
			<main className="flex-1">
				<Outlet />
			</main>
			<Footer />
		</div>
	);
}
