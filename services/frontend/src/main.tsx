import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRouter, RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ErrorBoundary } from "@/components/layout/ErrorBoundary";
import { AuthProvider } from "@/lib/auth";
import { RolesProvider } from "@/lib/roles";
import { ThemeProvider } from "@/lib/theme";
import { ToastsProvider } from "@/lib/toasts";
import { routeTree } from "./routeTree.gen";
import "./styles/index.css";

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 30_000,
			retry: 1,
			refetchOnWindowFocus: false,
		},
	},
});

const router = createRouter({
	routeTree,
	defaultPreload: "intent",
	defaultPreloadStaleTime: 0,
	context: { queryClient },
});

declare module "@tanstack/react-router" {
	interface Register {
		router: typeof router;
	}
}

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("#root element missing from index.html");

createRoot(rootEl).render(
	<StrictMode>
		<QueryClientProvider client={queryClient}>
			<ThemeProvider>
				<AuthProvider>
					<RolesProvider>
						<ToastsProvider>
							<ErrorBoundary>
								<RouterProvider router={router} />
							</ErrorBoundary>
						</ToastsProvider>
					</RolesProvider>
				</AuthProvider>
			</ThemeProvider>
		</QueryClientProvider>
	</StrictMode>,
);
