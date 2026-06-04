import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { listCategories } from "@/lib/api";

export const Route = createFileRoute("/app/explore/categories")({
	component: CategoriesRoute,
});

function CategoriesRoute() {
	const q = useQuery({ queryKey: ["categories"], queryFn: listCategories });

	return (
		<div className="mx-auto max-w-2xl space-y-6">
			<PageHeader title="Categories" description="Curated taxonomy." />
			{q.isLoading ? (
				<Skeleton className="h-64" />
			) : !q.data || q.data.length === 0 ? (
				<EmptyState title="No categories" />
			) : (
				<ul className="divide-y divide-border border border-border">
					{q.data.map((c) => (
						<li
							key={c.category_id}
							className="bg-bg p-3"
							style={{ paddingLeft: 12 + c.depth * 16 }}
						>
							<div>{c.display_name}</div>
							<div className="text-xs uppercase tracking-widest text-fg-subtle">
								{c.category_id}
								{c.parent_id ? ` · parent ${c.parent_id}` : ""}
							</div>
						</li>
					))}
				</ul>
			)}
		</div>
	);
}
