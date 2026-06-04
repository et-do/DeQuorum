import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { getLineage } from "@/lib/api";

export const Route = createFileRoute("/app/explore/lineages/$id")({
	component: LineageDetail,
});

function LineageDetail() {
	const { id } = Route.useParams();
	const q = useQuery({
		queryKey: ["lineage", id],
		queryFn: () => getLineage(id),
	});

	if (q.isLoading) return <Skeleton className="h-64" />;
	if (!q.data) return <EmptyState title="Lineage not found" />;

	const lineage = q.data;
	return (
		<div className="mx-auto max-w-3xl space-y-6">
			<PageHeader
				eyebrow="Lineage"
				title={lineage.lineage_id}
				description={`${lineage.versions.length} version${
					lineage.versions.length === 1 ? "" : "s"
				}`}
			/>

			<ol className="space-y-3 border-l border-border pl-6">
				{lineage.versions.map((v) => (
					<li key={v.contribution_id}>
						<div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-widest text-fg-subtle">
							<span>v{v.version_number}</span>
							{v.status && (
								<Badge
									tone={
										v.status === "approved"
											? "success"
											: v.status === "rejected"
												? "danger"
												: "muted"
									}
								>
									{v.status}
								</Badge>
							)}
							<span>tally {v.tally >= 0 ? `+${v.tally}` : v.tally}</span>
						</div>
						<Link
							to="/app/explore/contributions/$id"
							params={{ id: v.contribution_id }}
							className="font-bold tracking-tight hover:underline"
						>
							{v.expert_id}
						</Link>
						<p className="mt-1 text-sm text-fg-muted">{v.text}</p>
					</li>
				))}
			</ol>
		</div>
	);
}
