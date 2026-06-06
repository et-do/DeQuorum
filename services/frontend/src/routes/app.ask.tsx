import { createFileRoute, Outlet, useParams } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { SessionSidebar } from "@/components/chat/SessionSidebar";
import { withAuthHeader } from "@/lib/auth";

export const Route = createFileRoute("/app/ask")({
	component: AskLayout,
});

function AskLayout() {
	const params = useParams({ strict: false }) as { sessionId?: string };
	const [sidebarOpen, setSidebarOpen] = useState(false);

	// Pre-warm Ollama so the user's first message doesn't pay the
	// model-load cost. Fire-and-forget — failures are silently fine.
	useEffect(() => {
		(async () => {
			try {
				const auth = await withAuthHeader();
				await fetch("/api/v1/inference/warmup", {
					method: "POST",
					headers: { "Content-Type": "application/json", ...auth },
				});
			} catch {
				/* best-effort */
			}
		})();
	}, []);

	return (
		<div className="-mx-4 -my-6 flex h-[calc(100vh-2.5rem)] md:-mx-8 md:-my-10 md:h-screen">
			<SessionSidebar
				activeSessionId={params.sessionId}
				open={sidebarOpen}
				onClose={() => setSidebarOpen(false)}
			/>
			<div className="flex min-w-0 flex-1 flex-col">
				<button
					type="button"
					onClick={() => setSidebarOpen(true)}
					aria-label="Open sessions"
					className="flex h-10 items-center gap-2 bg-bg px-4 text-xs uppercase tracking-widest text-fg-muted hover:text-fg md:hidden"
				>
					☰ <span>Sessions</span>
				</button>
				<Outlet />
			</div>
		</div>
	);
}
