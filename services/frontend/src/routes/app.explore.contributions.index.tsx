import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import type { Contribution, Status } from "@/lib/api";
import { listCategories, listContributions } from "@/lib/api";

const STATUSES: { value: Status | ""; label: string }[] = [
	{ value: "", label: "All" },
	{ value: "pending", label: "Pending" },
	{ value: "approved", label: "Approved" },
	{ value: "rejected", label: "Rejected" },
	{ value: "superseded", label: "Superseded" },
];

interface SearchParams {
	category?: string;
	status?: Status;
	q?: string;
}

export const Route = createFileRoute("/app/explore/contributions/")({
	validateSearch: (search: Record<string, unknown>): SearchParams => ({
		category: typeof search.category === "string" ? search.category : undefined,
		status:
			search.status === "pending" ||
			search.status === "approved" ||
			search.status === "rejected" ||
			search.status === "superseded"
				? (search.status as Status)
				: undefined,
		q: typeof search.q === "string" ? search.q : undefined,
	}),
	component: ContributionsList,
});

function ContributionsList() {
	const navigate = useNavigate();
	const search = Route.useSearch();
	const [qInput, setQInput] = useState(search.q ?? "");

	useEffect(() => {
		const id = window.setTimeout(() => {
			navigate({
				to: "/app/explore/contributions",
				search: { ...search, q: qInput || undefined },
			});
		}, 250);
		return () => window.clearTimeout(id);
	}, [qInput, navigate, search]);

	const categories = useQuery({ queryKey: ["categories"], queryFn: listCategories });
	const contribs = useQuery({
		queryKey: ["contributions", search],
		queryFn: () => listContributions(search),
	});

	return (
		<div className="space-y-6">
			<PageHeader title="Contributions" description="All signed claims." />

			<div className="flex flex-wrap items-center gap-3">
				<input
					value={qInput}
					onChange={(e) => setQInput(e.target.value)}
					placeholder="Search text…"
					className="grow border border-border bg-bg px-3 py-2 text-sm focus:border-border-strong focus:outline-none"
				/>
				<select
					value={search.status ?? ""}
					onChange={(e) =>
						navigate({
							to: "/app/explore/contributions",
							search: {
								...search,
								status: (e.target.value || undefined) as Status | undefined,
							},
						})
					}
					className="border border-border bg-bg px-2 py-2 text-sm focus:border-border-strong focus:outline-none"
				>
					{STATUSES.map((s) => (
						<option key={s.value} value={s.value}>
							{s.label}
						</option>
					))}
				</select>
				<select
					value={search.category ?? ""}
					onChange={(e) =>
						navigate({
							to: "/app/explore/contributions",
							search: {
								...search,
								category: e.target.value || undefined,
							},
						})
					}
					className="border border-border bg-bg px-2 py-2 text-sm focus:border-border-strong focus:outline-none"
				>
					<option value="">All categories</option>
					{categories.data?.map((c) => (
						<option key={c.category_id} value={c.category_id}>
							{c.display_name}
						</option>
					))}
				</select>
			</div>

			{contribs.isLoading ? (
				<div className="space-y-2">
					<Skeleton className="h-16" />
					<Skeleton className="h-16" />
					<Skeleton className="h-16" />
				</div>
			) : !contribs.data || contribs.data.length === 0 ? (
				<EmptyState title="Nothing matches" description="Try clearing the filters." />
			) : (
				<ul className="divide-y divide-border border border-border">
					{contribs.data.map((c) => (
						<Row key={c.contribution_id} c={c} />
					))}
				</ul>
			)}
		</div>
	);
}

function Row({ c }: { c: Contribution }) {
	return (
		<li className="bg-bg p-4">
			<div className="flex flex-wrap items-baseline justify-between gap-2">
				<Link
					to="/app/explore/contributions/$id"
					params={{ id: c.contribution_id }}
					className="font-bold tracking-tight hover:underline"
				>
					{c.primary_category_id}
				</Link>
				<div className="flex items-center gap-2">
					{c.status && (
						<Badge
							tone={
								c.status === "approved" ? "success" : c.status === "rejected" ? "danger" : "muted"
							}
						>
							{c.status}
						</Badge>
					)}
					<span className="text-xs uppercase tracking-widest text-fg-subtle">
						tally {c.tally >= 0 ? `+${c.tally}` : c.tally}
					</span>
				</div>
			</div>
			<p className="mt-2 text-sm text-fg-muted">{c.text}</p>
		</li>
	);
}
