import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ExternalLink } from "@/components/ui/Link";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { getContribution } from "@/lib/api";

export const Route = createFileRoute("/app/explore/contributions/$id")({
	component: ContributionDetail,
});

function ContributionDetail() {
	const { id } = Route.useParams();
	const q = useQuery({
		queryKey: ["contribution", id],
		queryFn: () => getContribution(id),
	});

	if (q.isLoading) {
		return (
			<div className="space-y-4">
				<Skeleton className="h-10" />
				<Skeleton className="h-32" />
			</div>
		);
	}

	if (q.isError || !q.data) {
		return (
			<EmptyState
				title="Not found"
				description={(q.error as Error | null)?.message ?? "Unknown id."}
			/>
		);
	}

	const c = q.data;
	return (
		<div className="mx-auto max-w-3xl space-y-8">
			<PageHeader
				eyebrow={
					<span className="flex items-center gap-2">
						{c.status && (
							<Badge
								tone={
									c.status === "approved" ? "success" : c.status === "rejected" ? "danger" : "muted"
								}
							>
								{c.status}
							</Badge>
						)}
						<span>v{c.version_number}</span>
						<span>tally {c.tally >= 0 ? `+${c.tally}` : c.tally}</span>
					</span>
				}
				title={c.expert_id}
			/>

			<Card>
				<p className="text-fg">{c.text}</p>
				{c.citations.length > 0 && (
					<div className="mt-6 space-y-2">
						<div className="text-xs uppercase tracking-widest text-fg-subtle">Citations</div>
						<ul className="space-y-1">
							{c.citations.map((url) => (
								<li key={url} className="text-sm">
									<ExternalLink href={url} target="_blank">
										{url}
									</ExternalLink>
								</li>
							))}
						</ul>
					</div>
				)}
			</Card>

			<div className="grid gap-4 md:grid-cols-2">
				<Card>
					<CardHeader title="Lineage" subtitle={c.lineage_id} />
					<Link
						to="/app/explore/lineages/$id"
						params={{ id: c.lineage_id }}
						className="text-fg underline-offset-4 hover:underline"
					>
						View history →
					</Link>
				</Card>

				<Card>
					<CardHeader title="Contributor" />
					<Link
						to="/app/explore/contributors/$id"
						params={{ id: c.contributor_id }}
						className="flex items-center gap-3"
					>
						<Avatar seed={c.contributor_id} size={28} />
						<span className="text-fg hover:underline">{c.contributor_id}</span>
					</Link>
				</Card>
			</div>

			<Card>
				<CardHeader title={`Votes (${c.votes.length})`} />
				{c.votes.length === 0 ? (
					<p className="text-sm text-fg-muted">No votes yet.</p>
				) : (
					<ul className="space-y-1 text-sm text-fg-muted">
						{c.votes.map((v) => (
							<li key={v.vote_id}>
								<span className="text-fg">{v.voter_id}</span> ·{" "}
								{v.score >= 0 ? `+${v.score}` : v.score}
							</li>
						))}
					</ul>
				)}
			</Card>
		</div>
	);
}
