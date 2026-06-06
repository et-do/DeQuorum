/**
 * Module-level store for in-flight chat streams.
 *
 * Survives route unmounts (when the user navigates from session A to
 * session B mid-stream, A's stream keeps going). React components
 * subscribe via `useStream(sessionId)` and receive per-session updates
 * without re-rendering the rest of the tree.
 *
 * Usage:
 *
 *   const stream = useStream(sessionId);     // current state, or null
 *   const all = useActiveStreams();           // for sidebar indicators
 *   chatStreams.start(sessionId, text, ...);  // begin a stream
 *   chatStreams.stop(sessionId);              // abort the stream
 *
 * The store doesn't know about React Query directly — callers pass an
 * `onComplete` callback when starting a stream so they can invalidate
 * relevant queries themselves.
 */

import { useSyncExternalStore } from "react";
import type { ChatResponseEnvelope } from "@/lib/api";
import { streamChatMessage } from "@/lib/api";

export interface StreamState {
	sessionId: string;
	question: string;
	stage: string | null;
	chunks: string;
	response: ChatResponseEnvelope | null;
	/** New title emitted by the backend after the answer streams (if the
	 * session was due for auto-titling). The session-detail query + the
	 * sidebar list refetch will pick this up. */
	generatedTitle: string | null;
	error: string | null;
	abortController: AbortController;
}

type Listener = () => void;

class ChatStreamStore {
	private streams = new Map<string, StreamState>();
	private listeners = new Set<Listener>();

	private notify(): void {
		for (const l of this.listeners) l();
	}

	subscribe = (listener: Listener): (() => void) => {
		this.listeners.add(listener);
		return () => {
			this.listeners.delete(listener);
		};
	};

	getSnapshot = (): ReadonlyMap<string, StreamState> => this.streams;

	get(sessionId: string): StreamState | undefined {
		return this.streams.get(sessionId);
	}

	private update(sessionId: string, patch: Partial<StreamState>): void {
		const prev = this.streams.get(sessionId);
		if (!prev) return;
		this.streams.set(sessionId, { ...prev, ...patch });
		this.notify();
	}

	start(sessionId: string, question: string, onComplete?: (state: StreamState) => void): void {
		// Replace any prior stream for this session.
		this.streams.get(sessionId)?.abortController.abort();
		const abortController = new AbortController();
		const initial: StreamState = {
			sessionId,
			question,
			stage: null,
			chunks: "",
			response: null,
			generatedTitle: null,
			error: null,
			abortController,
		};
		this.streams.set(sessionId, initial);
		this.notify();

		streamChatMessage(sessionId, question, {
			signal: abortController.signal,
			onEvent: (event) => {
				if ("stage" in event) {
					this.update(sessionId, { stage: event.stage });
				} else if ("chunk" in event) {
					const cur = this.streams.get(sessionId);
					if (cur) this.update(sessionId, { chunks: cur.chunks + event.chunk });
				} else if ("done" in event) {
					this.update(sessionId, { response: event.done });
				} else if ("title" in event) {
					this.update(sessionId, { generatedTitle: event.title });
				} else if ("error" in event) {
					this.update(sessionId, { error: event.error });
				}
			},
		})
			.then(() => {
				const final = this.streams.get(sessionId);
				if (final && onComplete) onComplete(final);
				// Clear immediately. The session-detail refetch (kicked off by
				// onComplete) rehydrates the persisted user + assistant
				// messages — keeping the stream entry around would render the
				// same assistant turn twice once the refetch lands.
				if (this.streams.get(sessionId)?.abortController === abortController) {
					this.streams.delete(sessionId);
					this.notify();
				}
			})
			.catch((err: Error) => {
				if (abortController.signal.aborted) {
					this.streams.delete(sessionId);
					this.notify();
					return;
				}
				this.update(sessionId, { error: err.message });
			});
	}

	stop(sessionId: string): void {
		const stream = this.streams.get(sessionId);
		if (!stream) return;
		stream.abortController.abort();
		this.streams.delete(sessionId);
		this.notify();
	}

	isActive(sessionId: string): boolean {
		const s = this.streams.get(sessionId);
		return !!s && !s.response && !s.error;
	}
}

export const chatStreams = new ChatStreamStore();

export function useStream(sessionId: string | undefined): StreamState | null {
	const snapshot = useSyncExternalStore(
		chatStreams.subscribe,
		chatStreams.getSnapshot,
		chatStreams.getSnapshot,
	);
	return sessionId ? (snapshot.get(sessionId) ?? null) : null;
}

export function useActiveStreamIds(): ReadonlySet<string> {
	const snapshot = useSyncExternalStore(
		chatStreams.subscribe,
		chatStreams.getSnapshot,
		chatStreams.getSnapshot,
	);
	const set = new Set<string>();
	for (const [id, state] of snapshot) {
		if (!state.response && !state.error) set.add(id);
	}
	return set;
}
