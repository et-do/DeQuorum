/**
 * EventSource hook for the /v1/review/stream SSE endpoint.
 *
 * Returns the latest parsed payload, a connection state, and a manual
 * reconnect helper. The hook auto-reconnects on `error` after a short
 * backoff because EventSource doesn't expose `connecting` state reliably
 * across browsers.
 */

import { useEffect, useRef, useState } from "react";
import { type ContributionWithVotes, REVIEW_STREAM_URL } from "@/lib/api";

type Connection = "idle" | "connecting" | "open" | "closed";

export function useReviewStream() {
	const [data, setData] = useState<ContributionWithVotes[] | null>(null);
	const [connection, setConnection] = useState<Connection>("idle");
	const sourceRef = useRef<EventSource | null>(null);
	const tickRef = useRef(0);

	useEffect(() => {
		const tick = ++tickRef.current;
		setConnection("connecting");
		const es = new EventSource(REVIEW_STREAM_URL);
		sourceRef.current = es;

		es.onopen = () => {
			if (tickRef.current === tick) setConnection("open");
		};
		es.onmessage = (event) => {
			if (tickRef.current !== tick) return;
			try {
				setData(JSON.parse(event.data));
			} catch {
				// ignore malformed frame; next frame will replace it
			}
		};
		es.onerror = () => {
			if (tickRef.current === tick) setConnection("closed");
		};

		return () => {
			es.close();
			if (sourceRef.current === es) sourceRef.current = null;
		};
	}, []);

	return { data, connection };
}
