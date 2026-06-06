import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/Button";
import { type ChatSession, createChatSession } from "@/lib/api";
import { useToasts } from "@/lib/toasts";

export const Route = createFileRoute("/app/ask/")({
	component: AskHome,
});

const STARTERS = [
	"What's the difference between asyncio.gather and asyncio.wait?",
	"When should I reach for Rust's Pin?",
	"How does TCP congestion control actually work?",
	"What's the GIL's impact on Python threading?",
];

function AskHome() {
	const navigate = useNavigate();
	const qc = useQueryClient();
	const { toast } = useToasts();

	const createMut = useMutation({
		mutationFn: ({ prefill }: { prefill?: string }) =>
			createChatSession().then((s) => ({ session: s, prefill })),
		onSuccess: ({ session, prefill }) => {
			qc.setQueryData<ChatSession[]>(["chat", "sessions"], (prev) => [session, ...(prev ?? [])]);
			navigate({
				to: "/app/ask/$sessionId",
				params: { sessionId: session.session_id },
				search: prefill ? { prefill } : {},
			});
		},
		onError: (err: Error) => toast(err.message, { tone: "error", durationMs: 6000 }),
	});

	return (
		<div className="flex flex-1 items-center justify-center px-6">
			<div className="mx-auto max-w-2xl space-y-6 text-center">
				<div className="inline-flex h-12 w-12 items-center justify-center border border-border-strong text-lg font-bold tracking-widest">
					DQ
				</div>
				<div className="space-y-2">
					<h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
						What do you want to know?
					</h1>
					<p className="text-sm text-fg-muted">
						Your question gets routed to the expert panel that owns the topic. Every answer cites
						the contributors whose knowledge shaped it.
					</p>
				</div>

				<div className="grid gap-2 sm:grid-cols-2">
					{STARTERS.map((s) => (
						<button
							type="button"
							key={s}
							onClick={() => createMut.mutate({ prefill: s })}
							disabled={createMut.isPending}
							className="border border-border bg-bg p-3 text-left text-sm text-fg-muted transition-colors hover:border-border-strong hover:bg-bg-muted hover:text-fg disabled:cursor-not-allowed disabled:opacity-50"
						>
							{s}
						</button>
					))}
				</div>

				<div>
					<Button size="lg" onClick={() => createMut.mutate({})} disabled={createMut.isPending}>
						{createMut.isPending ? "Creating…" : "Start a new chat"}
					</Button>
				</div>
			</div>
		</div>
	);
}
