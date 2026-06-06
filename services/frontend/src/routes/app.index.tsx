import { createFileRoute, redirect } from "@tanstack/react-router";

/**
 * /app lands directly in chat. The old contribution-counter dashboard
 * was an admin view that didn't match what a user actually wants when
 * they open the app — chat is the primary surface, à la ChatGPT /
 * Claude. Contribution metrics live on /app/explore/contributions
 * and the contributor pipeline lives on /app/contribute + /app/review.
 */
export const Route = createFileRoute("/app/")({
	beforeLoad: () => {
		throw redirect({ to: "/app/ask" });
	},
});
