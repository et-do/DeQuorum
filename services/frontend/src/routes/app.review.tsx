import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import type { ContributionWithVotes } from "@/lib/api";
import { castVote, getReviewQueue } from "@/lib/api";
import { useToasts } from "@/lib/toasts";
import { useReviewStream } from "@/lib/useReviewStream";

export const Route = createFileRoute("/app/review")({
	component: ReviewRoute,
	loader: async () => {
		const queue = await getReviewQueue();
		return { queue };
	},
});

function ReviewRoute() {
	const { queue: initialQueue } = Route.useLoaderData();
	const stream = useReviewStream();
	const queue = stream.data ?? initialQueue;

	return (
		<div className="space-y-8">
			<PageHeader
				title="Review queue"
				description={`${queue.length} pending`}
				eyebrow={`stream ${stream.connection}`}
			/>

			{queue.length === 0 ? (
				<EmptyState
					title="Caught up"
					description="No pending submissions right now. The stream will update this view live."
				/>
			) : (
				<ul className="space-y-3">
					{queue.map((c) => (
						<ReviewCard key={c.contribution_id} c={c} />
					))}
				</ul>
			)}
		</div>
	);
}

function ReviewCard({ c }: { c: ContributionWithVotes }) {
	const qc = useQueryClient();
	const { toast } = useToasts();

	const mutation = useMutation({
		mutationFn: (score: -1 | 0 | 1) => castVote(c.contribution_id, { score }),
		onSuccess: (res) => {
			qc.invalidateQueries({ queryKey: ["contributions"] });
			toast(`Vote cast · tally ${res.tally >= 0 ? `+${res.tally}` : res.tally}`, {
				tone: "success",
			});
		},
		onError: (e: Error) => toast(e.message, { tone: "error", durationMs: 8000 }),
	});

	// biome-ignore lint/correctness/useExhaustiveDependencies: intentional reset on contribution change only
	useEffect(() => mutation.reset(), [c.contribution_id]);

	return (
		<li>
			<Card>
				<div className="flex flex-wrap items-baseline justify-between gap-2">
					<Link
						to="/app/explore/contributions/$id"
						params={{ id: c.contribution_id }}
						className="font-bold tracking-tight hover:underline"
					>
						{c.primary_category_id}
					</Link>
					<Badge tone="muted">tally {c.tally >= 0 ? `+${c.tally}` : c.tally}</Badge>
				</div>
				<p className="mt-3 text-sm text-fg-muted">{c.text}</p>

				<div className="mt-4 flex flex-wrap items-center gap-3">
					<Button variant="ghost" onClick={() => mutation.mutate(1)} disabled={mutation.isPending}>
						+1
					</Button>
					<Button variant="ghost" onClick={() => mutation.mutate(0)} disabled={mutation.isPending}>
						0
					</Button>
					<Button variant="ghost" onClick={() => mutation.mutate(-1)} disabled={mutation.isPending}>
						-1
					</Button>
				</div>
			</Card>
		</li>
	);
}
