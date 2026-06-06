import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { getContributor } from "@/lib/api";

export const Route = createFileRoute("/app/explore/contributors/$id")({
	component: ContributorDetail,
});

function ContributorDetail() {
	const { id } = Route.useParams();
	const q = useQuery({
		queryKey: ["contributor", id],
		queryFn: () => getContributor(id),
	});

	if (q.isLoading) return <Skeleton className="h-40" />;
	if (!q.data) return <EmptyState title="Not found" />;

	const c = q.data;

	return (
		<div className="space-y-6">
			<PageHeader
				eyebrow={
					<Badge tone="muted">
						Tier {c.tier} · {c.tier_name}
					</Badge>
				}
				title={
					<span className="flex items-center gap-3">
						<Avatar seed={c.contributor_id} size={32} />
						<span>{c.display_name}</span>
					</span>
				}
				description={c.contributor_id}
			/>

			<Card>
				<CardHeader title={`Contributions (${c.contributions.length})`} />
				{c.contributions.length === 0 ? (
					<EmptyState title="Nothing yet" />
				) : (
					<ul className="divide-y divide-border">
						{c.contributions.map((co) => (
							<li
								key={co.contribution_id}
								className="flex items-baseline justify-between gap-3 py-3"
							>
								<Link
									to="/app/explore/contributions/$id"
									params={{ id: co.contribution_id }}
									className="hover:underline"
								>
									{co.primary_category_id}
								</Link>
								<span className="text-xs uppercase tracking-widest text-fg-subtle">
									{co.status} · {co.tally >= 0 ? `+${co.tally}` : co.tally}
								</span>
							</li>
						))}
					</ul>
				)}
			</Card>
		</div>
	);
}
