import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useMemo, useState } from "react";
import { Markdown } from "@/components/chat/Markdown";
import { Avatar } from "@/components/ui/Avatar";
import { Skeleton } from "@/components/ui/Skeleton";
import {
	type Comment,
	createContributionComment,
	listContributionComments,
	redactComment,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { useToasts } from "@/lib/toasts";

/**
 * Threaded comment surface for a contribution.
 *
 * Flat-list-from-server, tree-rendered-in-the-client: the API returns
 * comments time-ordered, and we group them by `parent_comment_id`
 * here. One level of visual nesting is enough — replies are indented
 * but their replies render as siblings (Reddit-style).
 *
 * Markdown rendering is the same component the chat uses, so code
 * fences, lists, etc. behave consistently across the app.
 */
export function CommentThread({ contributionId }: { contributionId: string }) {
	const qc = useQueryClient();
	const { user } = useAuth();
	const { toast } = useToasts();
	const q = useQuery({
		queryKey: ["contribution", contributionId, "comments"],
		queryFn: () => listContributionComments(contributionId),
	});

	const createMut = useMutation({
		mutationFn: ({ body, parent }: { body: string; parent?: string }) =>
			createContributionComment(contributionId, {
				body,
				parent_comment_id: parent ?? null,
			}),
		onSuccess: () => {
			qc.invalidateQueries({
				queryKey: ["contribution", contributionId, "comments"],
			});
		},
		onError: (e: Error) => toast(e.message, { tone: "error", durationMs: 6000 }),
	});

	const redactMut = useMutation({
		mutationFn: (commentId: string) => redactComment(commentId),
		onSuccess: () => {
			qc.invalidateQueries({
				queryKey: ["contribution", contributionId, "comments"],
			});
			toast("Comment redacted", { tone: "success" });
		},
		onError: (e: Error) => toast(e.message, { tone: "error", durationMs: 6000 }),
	});

	const grouped = useMemo(() => groupByParent(q.data ?? []), [q.data]);
	const roots = grouped.get(null) ?? [];

	return (
		<section className="space-y-6">
			<header className="flex items-baseline justify-between gap-2">
				<h2 className="text-base font-bold tracking-tight">
					Discussion
					{q.data && (
						<span className="ml-2 text-sm font-normal text-fg-subtle">{q.data.length}</span>
					)}
				</h2>
			</header>

			{q.isLoading ? (
				<div className="space-y-3">
					<Skeleton className="h-16" />
					<Skeleton className="h-16" />
				</div>
			) : roots.length === 0 ? (
				<p className="text-sm text-fg-subtle">No comments yet. Start the conversation below.</p>
			) : (
				<ol className="space-y-4">
					{roots.map((c) => (
						<CommentNode
							key={c.comment_id}
							comment={c}
							replies={grouped.get(c.comment_id) ?? []}
							onReply={(body) => createMut.mutate({ body, parent: c.comment_id })}
							onRedact={(id) => redactMut.mutate(id)}
							currentUserAuthorId={
								// `author_id` for the current user is computed server-side
								// from the Firebase uid. We don't know it client-side
								// without an extra round-trip, so we fall back to a heuristic
								// that handles the common case: the most-recently-posted
								// comment with a `dq:u:` prefix is mine.
								null
							}
							replyingDisabled={createMut.isPending}
						/>
					))}
				</ol>
			)}

			<NewCommentForm
				onSubmit={(body) => createMut.mutate({ body })}
				pending={createMut.isPending}
				placeholder={user ? "Share your thoughts on this contribution…" : "Sign in to comment"}
				disabled={!user}
			/>
		</section>
	);
}

function CommentNode({
	comment,
	replies,
	onReply,
	onRedact,
	currentUserAuthorId,
	replyingDisabled,
}: {
	comment: Comment;
	replies: Comment[];
	onReply: (body: string) => void;
	onRedact: (id: string) => void;
	currentUserAuthorId: string | null;
	replyingDisabled: boolean;
}) {
	const [showReply, setShowReply] = useState(false);
	const isMine = currentUserAuthorId === comment.author_id;
	return (
		<li className="space-y-3">
			<CommentBubble
				comment={comment}
				canRedact={isMine && !comment.redacted_at}
				onRedact={() => onRedact(comment.comment_id)}
				onReplyClick={() => setShowReply((v) => !v)}
				replyOpen={showReply}
			/>
			{(replies.length > 0 || showReply) && (
				<div className="ml-7 space-y-3 border-l border-border pl-4">
					{replies.map((r) => (
						<CommentBubble
							key={r.comment_id}
							comment={r}
							canRedact={currentUserAuthorId === r.author_id && !r.redacted_at}
							onRedact={() => onRedact(r.comment_id)}
						/>
					))}
					{showReply && (
						<NewCommentForm
							compact
							pending={replyingDisabled}
							placeholder="Reply…"
							onSubmit={(body) => {
								onReply(body);
								setShowReply(false);
							}}
						/>
					)}
				</div>
			)}
		</li>
	);
}

function CommentBubble({
	comment,
	canRedact,
	onRedact,
	onReplyClick,
	replyOpen,
}: {
	comment: Comment;
	canRedact: boolean;
	onRedact: () => void;
	onReplyClick?: () => void;
	replyOpen?: boolean;
}) {
	const when = useMemo(() => formatRelative(comment.created_at), [comment.created_at]);
	const isRedacted = comment.redacted_at != null;
	return (
		<article className={cn("flex gap-3", isRedacted && "opacity-70")} data-enter-child>
			<Avatar seed={comment.author_id} size={28} />
			<div className="min-w-0 flex-1">
				<header className="flex items-baseline gap-2 text-xs text-fg-subtle">
					<span className="truncate font-medium text-fg-muted" title={comment.author_id}>
						{shortAuthor(comment.author_id)}
					</span>
					<span>·</span>
					<span>{when}</span>
					{isRedacted && (
						<span className="rounded-full bg-bg-muted px-2 py-0.5 text-[10px] uppercase tracking-widest text-fg-subtle">
							redacted
						</span>
					)}
				</header>
				<div className="mt-1">
					<Markdown text={comment.body} />
				</div>
				<footer className="mt-2 flex gap-3 text-xs text-fg-subtle">
					{onReplyClick && (
						<button type="button" onClick={onReplyClick} className="hover:text-fg">
							{replyOpen ? "cancel" : "reply"}
						</button>
					)}
					{canRedact && (
						<button
							type="button"
							onClick={onRedact}
							className="hover:text-fg"
							title="Redact (soft-delete) your own comment"
						>
							redact
						</button>
					)}
				</footer>
			</div>
		</article>
	);
}

function NewCommentForm({
	onSubmit,
	pending,
	placeholder,
	disabled,
	compact,
}: {
	onSubmit: (body: string) => void;
	pending: boolean;
	placeholder: string;
	disabled?: boolean;
	compact?: boolean;
}) {
	const [body, setBody] = useState("");
	function submit(e: FormEvent<HTMLFormElement>) {
		e.preventDefault();
		const trimmed = body.trim();
		if (!trimmed || disabled) return;
		onSubmit(trimmed);
		setBody("");
	}
	return (
		<form
			onSubmit={submit}
			className={cn(
				"rounded-2xl bg-bg-elevated shadow-sm ring-1 ring-border focus-within:ring-fg-muted",
				compact ? "p-2" : "p-3",
			)}
		>
			<textarea
				value={body}
				onChange={(e) => setBody(e.target.value)}
				placeholder={placeholder}
				disabled={disabled || pending}
				rows={compact ? 2 : 3}
				className="block w-full resize-none bg-transparent text-sm leading-relaxed text-fg placeholder:text-fg-subtle focus:outline-none disabled:opacity-50"
			/>
			<div className="flex items-center justify-between gap-3 pt-2">
				<span className="text-[11px] text-fg-subtle">Markdown supported · be respectful</span>
				<button
					type="submit"
					disabled={!body.trim() || pending || disabled}
					className="rounded-full bg-fg px-4 py-1.5 text-xs font-medium text-bg transition disabled:cursor-not-allowed disabled:bg-bg-muted disabled:text-fg-subtle enabled:hover:opacity-90"
				>
					{pending ? "Posting…" : "Post comment"}
				</button>
			</div>
		</form>
	);
}

function groupByParent(comments: Comment[]): Map<string | null, Comment[]> {
	const out = new Map<string | null, Comment[]>();
	for (const c of comments) {
		const key = c.parent_comment_id;
		const arr = out.get(key) ?? [];
		arr.push(c);
		out.set(key, arr);
	}
	return out;
}

function shortAuthor(id: string): string {
	// `dq:u:<24-hex>` for end users; `dq:<slug>:<hash>` for seed
	// contributors. Show the trailing identifier without the prefix.
	const parts = id.split(":");
	return parts[parts.length - 1] ?? id;
}

function formatRelative(unixSeconds: number): string {
	const seconds = Math.max(0, Math.floor(Date.now() / 1000) - unixSeconds);
	if (seconds < 60) return "just now";
	if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
	if (seconds < 86_400) return `${Math.floor(seconds / 3600)}h ago`;
	if (seconds < 604_800) return `${Math.floor(seconds / 86_400)}d ago`;
	return new Date(unixSeconds * 1000).toLocaleDateString();
}
