import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { listContributors } from "@/lib/api";

export const Route = createFileRoute("/app/explore/contributors/")({
	component: ContributorsList,
});

function ContributorsList() {
	const q = useQuery({
		queryKey: ["contributors"],
		queryFn: listContributors,
	});

	return (
		<div className="space-y-6">
			<PageHeader title="Contributors" description={`${q.data?.length ?? "…"} accounts.`} />

			{q.isLoading ? (
				<div className="space-y-2">
					<Skeleton className="h-14" />
					<Skeleton className="h-14" />
				</div>
			) : !q.data || q.data.length === 0 ? (
				<EmptyState title="No contributors yet" />
			) : (
				<ul className="divide-y divide-border border border-border">
					{q.data.map((c) => (
						<li key={c.contributor_id} className="bg-bg p-4">
							<Link
								to="/app/explore/contributors/$id"
								params={{ id: c.contributor_id }}
								className="flex items-center justify-between gap-3"
							>
								<div className="flex items-center gap-3 min-w-0">
									<Avatar seed={c.contributor_id} size={28} />
									<div className="min-w-0">
										<div className="truncate font-bold tracking-tight">{c.display_name}</div>
										<div className="truncate text-xs uppercase tracking-widest text-fg-subtle">
											{c.contributor_id}
										</div>
									</div>
								</div>
								<Badge tone="muted">
									Tier {c.tier} · {c.tier_name}
								</Badge>
							</Link>
						</li>
					))}
				</ul>
			)}
		</div>
	);
}
