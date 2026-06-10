import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { ResizableSidebar } from "@/components/layout/ResizableSidebar";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import {
	type ChatSession,
	createChatSession,
	deleteChatSession,
	listChatSessions,
	renameChatSession,
} from "@/lib/api";
import { useActiveStreamIds } from "@/lib/chatStreams";
import { cn } from "@/lib/cn";
import { useToasts } from "@/lib/toasts";

/**
 * Chat-history sidebar. Wraps `ResizableSidebar` so the user can drag
 * to resize, collapse to icon-only, or open as a drawer on mobile.
 *
 * Sessions are scoped to the signed-in Firebase user; auth is enforced
 * at the API layer so an unauthenticated `listChatSessions()` 401s.
 */
export function SessionSidebar({
	activeSessionId,
	open,
	onClose,
}: {
	activeSessionId?: string;
	open: boolean;
	onClose: () => void;
}) {
	const navigate = useNavigate();
	const qc = useQueryClient();
	const { toast } = useToasts();
	const activeStreams = useActiveStreamIds();

	const sessionsQ = useQuery({
		queryKey: ["chat", "sessions"],
		queryFn: () => listChatSessions(),
	});

	const createMut = useMutation({
		mutationFn: () => createChatSession(),
		onSuccess: (session) => {
			qc.setQueryData<ChatSession[]>(["chat", "sessions"], (prev) => [session, ...(prev ?? [])]);
			navigate({
				to: "/app/ask/$sessionId",
				params: { sessionId: session.session_id },
			});
			onClose();
		},
		onError: (err: Error) => toast(err.message, { tone: "error", durationMs: 6000 }),
	});

	return (
		<ResizableSidebar
			id="chat-sessions"
			aria-label="Chat sessions"
			mobileOpen={open}
			onMobileClose={onClose}
			defaultWidth={280}
			minWidth={220}
			maxWidth={400}
		>
			{({ collapsed, toggleCollapsed }) => (
				<>
					<div className="px-3 py-3">
						<button
							type="button"
							onClick={() => createMut.mutate()}
							disabled={createMut.isPending}
							title="New chat"
							className={cn(
								"flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-fg-muted ring-1 ring-border transition-colors hover:bg-bg-elevated hover:text-fg",
								collapsed && "justify-center px-2",
							)}
						>
							<span aria-hidden="true" className="text-base leading-none">
								+
							</span>
							{!collapsed && <span>New chat</span>}
						</button>
					</div>

					<div className="flex-1 overflow-y-auto px-2 py-3">
						{sessionsQ.isLoading ? (
							<div className="space-y-2">
								<Skeleton className="h-10" />
								<Skeleton className="h-10" />
								<Skeleton className="h-10" />
							</div>
						) : !sessionsQ.data || sessionsQ.data.length === 0 ? (
							!collapsed && (
								<EmptyState
									title="No sessions yet"
									description="Start a new chat to see it here."
								/>
							)
						) : (
							<ul className="space-y-1" data-enter>
								{sessionsQ.data.map((s) => (
									<SessionRow
										key={s.session_id}
										session={s}
										active={activeSessionId === s.session_id}
										streaming={activeStreams.has(s.session_id)}
										collapsed={collapsed}
										onClick={onClose}
									/>
								))}
							</ul>
						)}
					</div>
					{/* Footer box mirrors AppShell's exactly: px-2 pb-2 wrapper around a
					    px-3 py-2 row, with an h-8 button. AppShell's collapse button
					    centers in a 32px row set by the h-8 ThemeToggle; making this
					    button h-8 too gives an identical 32px content row, so both
					    collapse buttons share the same vertical center. */}
					<div className="px-2 pb-2">
						<div
							className={cn(
								"flex items-center px-3 py-2",
								collapsed ? "justify-center" : "justify-end",
							)}
						>
							<button
								type="button"
								onClick={toggleCollapsed}
								aria-label={collapsed ? "Expand sessions" : "Collapse sessions"}
								title={collapsed ? "Expand sessions" : "Collapse sessions"}
								className="flex h-8 w-8 items-center justify-center rounded-md text-xs text-fg-subtle transition-colors hover:bg-bg-muted hover:text-fg"
							>
								{collapsed ? "›" : "‹"}
							</button>
						</div>
					</div>
				</>
			)}
		</ResizableSidebar>
	);
}

function SessionRow({
	session,
	active,
	streaming,
	collapsed,
	onClick,
}: {
	session: ChatSession;
	active: boolean;
	streaming: boolean;
	collapsed: boolean;
	onClick: () => void;
}) {
	const qc = useQueryClient();
	const navigate = useNavigate();
	const { toast } = useToasts();
	const params = useParams({ strict: false }) as { sessionId?: string };
	const [confirming, setConfirming] = useState(false);
	const [editing, setEditing] = useState(false);
	const [draft, setDraft] = useState(session.title);
	const inputRef = useRef<HTMLInputElement>(null);

	useEffect(() => setDraft(session.title), [session.title]);
	useEffect(() => {
		if (editing) inputRef.current?.select();
	}, [editing]);

	const deleteMut = useMutation({
		mutationFn: () => deleteChatSession(session.session_id),
		onSuccess: () => {
			qc.setQueryData<ChatSession[]>(["chat", "sessions"], (prev) =>
				(prev ?? []).filter((s) => s.session_id !== session.session_id),
			);
			if (params.sessionId === session.session_id) {
				navigate({ to: "/app/ask" });
			}
			toast("Session deleted", { tone: "success" });
		},
		onError: (err: Error) => toast(err.message, { tone: "error", durationMs: 6000 }),
	});

	const renameMut = useMutation({
		mutationFn: (title: string) => renameChatSession(session.session_id, title),
		onSuccess: (updated) => {
			qc.setQueryData<ChatSession[]>(["chat", "sessions"], (prev) =>
				(prev ?? []).map((s) => (s.session_id === updated.session_id ? updated : s)),
			);
			qc.invalidateQueries({
				queryKey: ["chat", "session", session.session_id],
			});
		},
		onError: (err: Error) => toast(err.message, { tone: "error", durationMs: 6000 }),
	});

	function commit() {
		const next = draft.trim();
		if (!next || next === session.title) {
			setEditing(false);
			setDraft(session.title);
			return;
		}
		renameMut.mutate(next);
		setEditing(false);
	}

	function cancel() {
		setEditing(false);
		setDraft(session.title);
	}

	function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
		if (e.key === "Enter") {
			e.preventDefault();
			commit();
		} else if (e.key === "Escape") {
			e.preventDefault();
			cancel();
		}
	}

	if (collapsed) {
		return (
			<li>
				<Link
					to="/app/ask/$sessionId"
					params={{ sessionId: session.session_id }}
					onClick={onClick}
					title={session.title}
					className={cn(
						"flex h-9 items-center justify-center rounded-md text-xs",
						active ? "bg-fg text-bg" : "text-fg-muted hover:bg-bg-muted hover:text-fg",
					)}
				>
					{streaming ? (
						<span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
					) : (
						session.title.slice(0, 2).toUpperCase()
					)}
				</Link>
			</li>
		);
	}

	return (
		<li className="group relative" data-enter-child>
			<Link
				to="/app/ask/$sessionId"
				params={{ sessionId: session.session_id }}
				onClick={(e) => {
					if (editing) e.preventDefault();
					else onClick();
				}}
				onDoubleClick={(e) => {
					e.preventDefault();
					setEditing(true);
				}}
				className={cn(
					"block truncate rounded-md px-3 py-2 pr-16 text-sm transition-colors",
					active ? "bg-fg text-bg" : "text-fg-muted hover:bg-bg-muted hover:text-fg",
				)}
			>
				{editing ? (
					<input
						ref={inputRef}
						value={draft}
						onChange={(e) => setDraft(e.target.value)}
						onKeyDown={onKeyDown}
						onBlur={commit}
						onClick={(e) => e.preventDefault()}
						className={cn(
							"-mx-1 -my-0.5 block w-[calc(100%+0.5rem)] rounded-sm border bg-transparent px-1 py-0.5 text-sm font-medium focus:outline-none",
							active
								? "border-bg/40 text-bg placeholder:text-bg/50"
								: "border-border-strong text-fg",
						)}
					/>
				) : (
					<span className="block truncate font-medium">
						{streaming && (
							<span
								aria-hidden="true"
								className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-current align-middle"
							/>
						)}
						{session.title}
					</span>
				)}
				<span className={cn("block truncate text-xs", active ? "text-bg/70" : "text-fg-subtle")}>
					{streaming ? "Composing…" : formatRelative(session.updated_at)}
				</span>
			</Link>
			{!editing && (
				<div
					className={cn(
						"absolute right-1 top-1.5 hidden gap-0.5 group-hover:flex",
						active ? "text-bg" : "text-fg-subtle",
					)}
				>
					<button
						type="button"
						onClick={(e) => {
							e.stopPropagation();
							e.preventDefault();
							setEditing(true);
						}}
						aria-label="Rename session"
						className={cn(
							"flex h-6 w-6 items-center justify-center rounded text-xs",
							active ? "hover:bg-bg/20" : "hover:bg-bg-elevated hover:text-fg",
						)}
					>
						✎
					</button>
					<button
						type="button"
						onClick={(e) => {
							e.stopPropagation();
							e.preventDefault();
							if (!confirming) {
								setConfirming(true);
								window.setTimeout(() => setConfirming(false), 2500);
							} else {
								deleteMut.mutate();
							}
						}}
						aria-label={confirming ? "Confirm delete" : "Delete session"}
						className={cn(
							"flex h-6 w-6 items-center justify-center rounded text-xs",
							active ? "hover:bg-bg/20" : "hover:bg-bg-elevated hover:text-fg",
							confirming && "bg-fg-muted text-bg",
						)}
					>
						{confirming ? "✓" : "×"}
					</button>
				</div>
			)}
		</li>
	);
}

function formatRelative(unixSeconds: number): string {
	const seconds = Math.max(0, Math.floor(Date.now() / 1000) - unixSeconds);
	if (seconds < 60) return "just now";
	if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
	if (seconds < 86_400) return `${Math.floor(seconds / 3600)}h ago`;
	if (seconds < 604_800) return `${Math.floor(seconds / 86_400)}d ago`;
	return new Date(unixSeconds * 1000).toLocaleDateString();
}
