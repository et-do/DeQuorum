import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
	type FormEvent,
	type KeyboardEvent,
	useCallback,
	useEffect,
	useRef,
	useState,
} from "react";
import { Markdown } from "@/components/chat/Markdown";
import { Avatar } from "@/components/ui/Avatar";
import { Skeleton } from "@/components/ui/Skeleton";
import {
	type ChatMessage,
	type ChatSessionDetail,
	getChatSession,
	renameChatSession,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { chatStreams, type StreamState, useStream } from "@/lib/chatStreams";
import { useToasts } from "@/lib/toasts";

interface SearchParams {
	prefill?: string;
}

export const Route = createFileRoute("/app/ask/$sessionId")({
	component: SessionRoute,
	validateSearch: (s: Record<string, unknown>): SearchParams => ({
		prefill: typeof s.prefill === "string" ? s.prefill : undefined,
	}),
});

const STAGE_LABELS: Record<string, string> = {
	thinking: "Thinking",
	drawing_from_contributors: "Drawing from contributors",
	answering: "Answering",
	// Legacy stage names from earlier API revisions — keep so old streams
	// don't render a blank label.
	routing_question: "Thinking",
	finding_experts: "Thinking",
	retrieving_citations: "Drawing from contributors",
	composing_answer: "Answering",
};

function SessionRoute() {
	const { sessionId } = Route.useParams();
	const search = Route.useSearch();
	const navigate = useNavigate();
	const qc = useQueryClient();
	const { toast } = useToasts();
	const { user } = useAuth();
	const stream = useStream(sessionId);

	const sessionQ = useQuery({
		queryKey: ["chat", "session", sessionId],
		queryFn: () => getChatSession(sessionId),
	});

	const [input, setInput] = useState(search.prefill ?? "");
	const scrollRef = useRef<HTMLDivElement>(null);

	const send = useCallback(
		(text: string) => {
			const question = text.trim();
			if (!question || stream) return;
			setInput("");
			// Optimistically append the user's bubble so it appears instantly
			// and the composing-turn below only needs to render the assistant
			// response. The session refetch on completion replaces this with
			// the real persisted record.
			qc.setQueryData<ChatSessionDetail>(["chat", "session", sessionId], (prev) => {
				if (!prev) return prev;
				const optimistic: ChatMessage = {
					message_id: `optimistic-${Date.now()}`,
					session_id: sessionId,
					role: "user",
					content: question,
					response: null,
					created_at: Date.now() / 1000,
					sequence_number: prev.messages.length,
				};
				return { ...prev, messages: [...prev.messages, optimistic] };
			});
			chatStreams.start(sessionId, question, () => {
				qc.invalidateQueries({ queryKey: ["chat", "session", sessionId] });
				qc.invalidateQueries({ queryKey: ["chat", "sessions"] });
			});
		},
		[sessionId, stream, qc],
	);

	// One-time prefill from /app/ask?prefill=... search param. Intentionally
	// only fires when the session finishes loading; capturing send/navigate/
	// search.prefill/sessionId in deps would re-fire the prefill on every
	// render and double-submit the seed question.
	// biome-ignore lint/correctness/useExhaustiveDependencies: one-shot effect
	useEffect(() => {
		if (!search.prefill || sessionQ.isLoading) return;
		send(search.prefill);
		navigate({
			to: "/app/ask/$sessionId",
			params: { sessionId },
			search: {},
			replace: true,
		});
	}, [sessionQ.isLoading]);

	function stop() {
		chatStreams.stop(sessionId);
		toast("Stopped", { tone: "info" });
	}

	function onSubmit(e: FormEvent<HTMLFormElement>) {
		e.preventDefault();
		send(input);
	}

	// Auto-scroll on new content. The deps are *triggers*, not values the
	// effect reads — we want a re-scroll any time messages change or the
	// stream updates, even though the effect body only touches the ref.
	// biome-ignore lint/correctness/useExhaustiveDependencies: trigger deps
	useEffect(() => {
		const el = scrollRef.current;
		if (!el) return;
		el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
	}, [sessionQ.data?.messages, stream]);

	const isComposing = !!stream && !stream.response && !stream.error;

	return (
		<div className="flex h-full flex-col">
			<EditableTitle sessionId={sessionId} title={sessionQ.data?.title} />

			<div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto px-4 py-6 md:px-8">
				{sessionQ.isLoading ? (
					<div className="mx-auto max-w-3xl space-y-3">
						<Skeleton className="h-16" />
						<Skeleton className="h-24" />
					</div>
				) : (
					<>
						{sessionQ.data?.messages.map((m) => (
							<Message key={m.message_id} message={m} userSeed={user?.uid ?? ""} />
						))}
						{stream && <ComposingTurn state={stream} />}
					</>
				)}
			</div>

			<Composer
				value={input}
				onChange={setInput}
				onSubmit={onSubmit}
				disabled={isComposing}
				composing={isComposing}
				onStop={stop}
			/>
		</div>
	);
}

// --- messages ----------------------------------------------------------

function Message({ message, userSeed }: { message: ChatMessage; userSeed: string }) {
	if (message.role === "user") {
		return <UserBubble text={message.content} seed={userSeed} />;
	}
	return <NetworkBubble content={message.content} />;
}

function UserBubble({ text, seed }: { text: string; seed: string }) {
	return (
		<div className="mx-auto flex max-w-3xl flex-row-reverse items-start gap-3">
			<Avatar seed={seed} size={28} />
			<div
				data-enter
				className="max-w-2xl whitespace-pre-wrap rounded-2xl bg-bg-elevated px-4 py-2.5 text-sm leading-relaxed"
			>
				{text}
			</div>
		</div>
	);
}

function NetworkBubble({ content }: { content: string }) {
	return (
		<div className="mx-auto flex max-w-3xl items-start gap-3">
			<NetworkAvatar />
			<div className="min-w-0 flex-1 space-y-3">
				<Markdown text={content} />
				<MessageActions text={content} />
			</div>
		</div>
	);
}

// Outer-ring node coordinates for the avatar mesh: 6 points evenly around the
// center of a 32×32 viewBox at radius 10.
const AVATAR_NODES = [
	[26, 16],
	[21, 24.66],
	[11, 24.66],
	[6, 16],
	[11, 7.34],
	[21, 7.34],
] as const;

function NetworkAvatar() {
	// A small DeQuorum mesh that rotates very slowly (see `.network-avatar-spin`
	// in styles/index.css; frozen under prefers-reduced-motion). Plain SVG so it
	// renders once per message with no canvas/rAF loop per bubble.
	return (
		<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-bg-elevated">
			<svg
				viewBox="0 0 32 32"
				className="network-avatar-spin h-5 w-5 text-fg-muted"
				role="img"
				aria-label="DeQuorum"
			>
				<g stroke="currentColor" strokeWidth="0.5" opacity="0.45">
					{AVATAR_NODES.map(([x, y], i) => {
						const [nx, ny] = AVATAR_NODES[(i + 1) % AVATAR_NODES.length];
						return (
							<g key={i}>
								<line x1="16" y1="16" x2={x} y2={y} />
								<line x1={x} y1={y} x2={nx} y2={ny} />
							</g>
						);
					})}
				</g>
				<g fill="currentColor">
					<circle cx="16" cy="16" r="2" />
					{AVATAR_NODES.map(([x, y], i) => (
						<circle key={i} cx={x} cy={y} r="1.5" />
					))}
				</g>
			</svg>
		</div>
	);
}

function ComposingTurn({ state }: { state: StreamState }) {
	return (
		<div className="mx-auto flex max-w-3xl items-start gap-3">
			<NetworkAvatar />
			<div className="min-w-0 flex-1 space-y-3">
				{state.error ? (
					<div className="text-sm text-fg-muted">Sorry — something went wrong. Try again?</div>
				) : state.chunks.length === 0 ? (
					<StageProgress activeStage={state.stage} />
				) : (
					<StreamedAnswer text={state.chunks} done={state.response !== null} />
				)}
			</div>
		</div>
	);
}

function StageProgress({ activeStage }: { activeStage: string | null }) {
	const label = (activeStage && STAGE_LABELS[activeStage]) || "Thinking";
	return (
		<div data-enter className="space-y-3">
			<div className="flex items-center gap-2 text-xs uppercase tracking-widest text-fg-subtle">
				<span className="inline-flex gap-1">
					<span className="h-1.5 w-1.5 animate-pulse rounded-full bg-fg-muted" />
					<span
						className="h-1.5 w-1.5 animate-pulse rounded-full bg-fg-muted"
						style={{ animationDelay: "150ms" }}
					/>
					<span
						className="h-1.5 w-1.5 animate-pulse rounded-full bg-fg-muted"
						style={{ animationDelay: "300ms" }}
					/>
				</span>
				<span>{label}…</span>
			</div>
			<div className="space-y-2">
				<div className="shimmer h-3 w-11/12 rounded bg-bg-muted/60" />
				<div
					className="shimmer h-3 w-10/12 rounded bg-bg-muted/60"
					style={{ animationDelay: "180ms" }}
				/>
				<div
					className="shimmer h-3 w-9/12 rounded bg-bg-muted/60"
					style={{ animationDelay: "360ms" }}
				/>
			</div>
		</div>
	);
}

function StreamedAnswer({ text, done }: { text: string; done: boolean }) {
	return (
		<div className="relative">
			<Markdown text={text} />
			{!done && (
				<span className="ml-0.5 inline-block h-4 w-2 -translate-y-px animate-pulse bg-fg align-middle" />
			)}
		</div>
	);
}

function MessageActions({ text }: { text: string }) {
	const { toast } = useToasts();
	const [copied, setCopied] = useState(false);
	return (
		<button
			type="button"
			onClick={async () => {
				try {
					await navigator.clipboard.writeText(text);
					setCopied(true);
					toast("Copied answer", { tone: "success" });
					window.setTimeout(() => setCopied(false), 1500);
				} catch {
					toast("Copy failed", { tone: "error" });
				}
			}}
			className="rounded-md px-2 py-1 text-xs uppercase tracking-widest text-fg-subtle hover:bg-bg-muted hover:text-fg"
		>
			{copied ? "✓ Copied" : "Copy"}
		</button>
	);
}

function Composer({
	value,
	onChange,
	onSubmit,
	disabled,
	composing,
	onStop,
}: {
	value: string;
	onChange: (v: string) => void;
	onSubmit: (e: FormEvent<HTMLFormElement>) => void;
	disabled: boolean;
	composing: boolean;
	onStop: () => void;
}) {
	const taRef = useRef<HTMLTextAreaElement>(null);

	// Autosize on every value change — biome sees `value` as an "outer
	// scope" trigger because the effect body only touches the ref, but
	// we genuinely want a re-measure each keystroke.
	// biome-ignore lint/correctness/useExhaustiveDependencies: value triggers re-measure
	useEffect(() => {
		const el = taRef.current;
		if (!el) return;
		el.style.height = "auto";
		const next = Math.min(el.scrollHeight, 240);
		el.style.height = `${next}px`;
	}, [value]);

	function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
		if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
			e.preventDefault();
			e.currentTarget.form?.requestSubmit();
		}
	}

	const canSend = !disabled && value.trim().length > 0;
	return (
		<form onSubmit={onSubmit} className="bg-bg px-4 py-4 md:px-8">
			<div className="mx-auto max-w-3xl">
				<div className="relative rounded-3xl bg-bg-elevated shadow-sm ring-1 ring-border transition-colors focus-within:ring-fg-muted">
					<textarea
						ref={taRef}
						value={value}
						onChange={(e) => onChange(e.target.value)}
						onKeyDown={onKeyDown}
						rows={1}
						placeholder="Ask anything…"
						disabled={disabled}
						className="block w-full resize-none bg-transparent px-5 py-4 pr-14 text-sm leading-relaxed text-fg placeholder:text-fg-subtle focus:outline-none disabled:opacity-50"
					/>
					<div className="absolute bottom-2.5 right-2.5">
						{composing ? (
							<button
								type="button"
								onClick={onStop}
								aria-label="Stop generating"
								className="flex h-9 w-9 items-center justify-center rounded-full bg-fg text-bg transition hover:opacity-90"
							>
								<span aria-hidden="true" className="block h-3 w-3 rounded-[2px] bg-bg" />
							</button>
						) : (
							<button
								type="submit"
								disabled={!canSend}
								aria-label="Send"
								className="flex h-9 w-9 items-center justify-center rounded-full bg-fg text-bg transition disabled:cursor-not-allowed disabled:bg-bg-muted disabled:text-fg-subtle enabled:hover:opacity-90"
							>
								<svg
									aria-hidden="true"
									viewBox="0 0 16 16"
									className="h-4 w-4"
									fill="none"
									stroke="currentColor"
									strokeWidth="2"
									strokeLinecap="round"
									strokeLinejoin="round"
								>
									<path d="M8 13V3" />
									<path d="M3.5 7.5L8 3l4.5 4.5" />
								</svg>
							</button>
						)}
					</div>
				</div>
				<p className="mt-2 text-center text-[11px] text-fg-subtle">
					Press <kbd className="rounded bg-bg-muted px-1.5 py-0.5">⌘</kbd>
					<span className="mx-1">+</span>
					<kbd className="rounded bg-bg-muted px-1.5 py-0.5">Enter</kbd>
					<span className="ml-1">to send</span>
				</p>
			</div>
		</form>
	);
}

// --- editable session title -------------------------------------------

function EditableTitle({ sessionId, title }: { sessionId: string; title: string | undefined }) {
	const qc = useQueryClient();
	const { toast } = useToasts();
	const [editing, setEditing] = useState(false);
	const [draft, setDraft] = useState(title ?? "");
	const inputRef = useRef<HTMLInputElement>(null);

	useEffect(() => {
		if (title !== undefined && !editing) setDraft(title);
	}, [title, editing]);

	useEffect(() => {
		if (editing) inputRef.current?.select();
	}, [editing]);

	const renameMut = useMutation({
		mutationFn: (next: string) => renameChatSession(sessionId, next),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: ["chat", "session", sessionId] });
			qc.invalidateQueries({ queryKey: ["chat", "sessions"] });
			toast("Title updated", { tone: "success" });
		},
		onError: (err: Error) => toast(err.message, { tone: "error", durationMs: 6000 }),
	});

	function commit() {
		const next = draft.trim();
		if (!next || next === title) {
			setEditing(false);
			setDraft(title ?? "");
			return;
		}
		renameMut.mutate(next);
		setEditing(false);
	}

	function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
		if (e.key === "Enter") {
			e.preventDefault();
			commit();
		} else if (e.key === "Escape") {
			e.preventDefault();
			setEditing(false);
			setDraft(title ?? "");
		}
	}

	return (
		<div className="px-6 pb-2 pt-4">
			<div className="text-xs uppercase tracking-widest text-fg-subtle">Session</div>
			{editing ? (
				<input
					ref={inputRef}
					value={draft}
					onChange={(e) => setDraft(e.target.value)}
					onKeyDown={onKeyDown}
					onBlur={commit}
					className="-mx-1 mt-0.5 block w-[calc(100%+0.5rem)] rounded-md bg-bg-elevated px-1 py-0.5 text-sm font-bold tracking-tight ring-1 ring-border focus:outline-none focus:ring-fg-muted"
				/>
			) : (
				<button
					type="button"
					onClick={() => setEditing(true)}
					title="Rename session"
					className="group flex w-full items-baseline gap-2 text-left"
				>
					<span className="truncate text-sm font-bold tracking-tight">{title ?? "…"}</span>
					<span
						aria-hidden="true"
						className="text-xs text-fg-subtle opacity-0 transition-opacity group-hover:opacity-100"
					>
						✎ rename
					</span>
				</button>
			)}
		</div>
	);
}
