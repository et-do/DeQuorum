import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { listContributions } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/app/contribute/")({
	component: ContributeIndex,
});

function ContributeIndex() {
	const { user } = useAuth();
	const mine = useQuery({
		queryKey: ["contributions", { contributor: user?.uid }],
		queryFn: () => listContributions(user ? { contributor: user.uid } : {}),
		enabled: !!user,
	});

	return (
		<div className="space-y-8">
			<PageHeader
				title="Contribute"
				description="File signed claims under a curated category."
				actions={
					<Link to="/app/contribute/new">
						<Button size="md">New submission</Button>
					</Link>
				}
			/>

			<Card>
				<CardHeader title="My contributions" subtitle={user?.uid ?? "unsigned"} />
				{!user ? (
					<EmptyState
						title="Not signed in"
						description="Sign in to track your contributions."
						action={
							<Link to="/signin">
								<Button>Sign in</Button>
							</Link>
						}
					/>
				) : mine.isLoading ? (
					<div className="space-y-2">
						<Skeleton className="h-12 w-full" />
						<Skeleton className="h-12 w-full" />
						<Skeleton className="h-12 w-full" />
					</div>
				) : !mine.data || mine.data.length === 0 ? (
					<EmptyState
						title="Nothing yet"
						description="Publish your first claim to see it here."
						action={
							<Link to="/app/contribute/new">
								<Button>New submission</Button>
							</Link>
						}
					/>
				) : (
					<ul className="divide-y divide-border">
						{mine.data.map((c) => (
							<li
								key={c.contribution_id}
								className="flex items-baseline justify-between gap-3 py-3"
							>
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
												c.status === "approved"
													? "success"
													: c.status === "rejected"
														? "danger"
														: "muted"
											}
										>
											{c.status}
										</Badge>
									)}
									<span className="text-xs uppercase tracking-widest text-fg-subtle">
										tally {c.tally >= 0 ? `+${c.tally}` : c.tally}
									</span>
								</div>
							</li>
						))}
					</ul>
				)}
			</Card>
		</div>
	);
}
