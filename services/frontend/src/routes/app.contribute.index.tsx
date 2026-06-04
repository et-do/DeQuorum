import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { useAccount } from "@/lib/account";
import { listContributions } from "@/lib/api";

export const Route = createFileRoute("/app/contribute/")({
	component: ContributeIndex,
});

function ContributeIndex() {
	const { account } = useAccount();
	const mine = useQuery({
		queryKey: ["contributions", { contributor: account?.contributor_id }],
		queryFn: () => listContributions(account ? { contributor: account.contributor_id } : {}),
		enabled: !!account,
	});

	return (
		<div className="space-y-8">
			<PageHeader
				title="Contribute"
				description="Publish signed claims tied to an expert persona."
				actions={
					<Link to="/app/contribute/new">
						<Button size="md">New submission</Button>
					</Link>
				}
			/>

			<Card>
				<CardHeader title="My contributions" subtitle={account?.contributor_id ?? "unsigned"} />
				{!account ? (
					<EmptyState
						title="No account"
						description="Sign up to track your contributions."
						action={
							<Link to="/app/account">
								<Button>Go to account</Button>
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
									{c.expert_id}
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
