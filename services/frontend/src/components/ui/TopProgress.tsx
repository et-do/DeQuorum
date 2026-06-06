import { useIsFetching, useIsMutating } from "@tanstack/react-query";

/**
 * Thin fixed-top progress bar that shows whenever React Query has at
 * least one query or mutation in flight. Doesn't track raw `fetch` or
 * the chat-stream loop — those have their own typewriter caret + stage
 * indicator. Purely "the network is doing something" feedback so the
 * UI never feels frozen between user input and visible response.
 */
export function TopProgress() {
	const fetching = useIsFetching();
	const mutating = useIsMutating();
	if (fetching + mutating === 0) return null;
	return <div role="progressbar" aria-label="Loading" className="top-progress" />;
}
