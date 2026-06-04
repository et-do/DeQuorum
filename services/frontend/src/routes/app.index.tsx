import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { useAccount } from "@/lib/account";
import type { Status } from "@/lib/api";
import { getMeta, listContributions } from "@/lib/api";
import { useRoles } from "@/lib/roles";

export const Route = createFileRoute("/app/")({
	component: AppDashboard,
});

function AppDashboard() {
	const { account } = useAccount();
	const { roles } = useRoles();
	const meta = useQuery({ queryKey: ["meta"], queryFn: getMeta });
	const contribs = useQuery({
		queryKey: ["contributions"],
		queryFn: () => listContributions(),
	});

	const counts =
		contribs.data?.reduce<Record<Status | "all", number>>(
			(acc, c) => {
				acc.all += 1;
				if (c.status) acc[c.status] = (acc[c.status] ?? 0) + 1;
				return acc;
			},
			{ all: 0, pending: 0, approved: 0, rejected: 0, superseded: 0 },
		) ?? null;

	return (
		<div className="space-y-10">
			<PageHeader
				eyebrow={account ? `Signed in as ${account.display_name}` : undefined}
				title="Dashboard"
				description={meta.data ? `${meta.data.use_mock ? "mock" : "live"} model · pool ready` : ""}
			/>

			<section className="grid grid-cols-2 gap-3 md:grid-cols-4">
				<StatTile label="Total" value={counts?.all ?? null} to="/app/explore/contributions" />
				<StatTile label="Pending" value={counts?.pending ?? null} to="/app/explore/contributions" />
				<StatTile
					label="Approved"
					value={counts?.approved ?? null}
					to="/app/explore/contributions"
				/>
				<StatTile
					label="Rejected"
					value={counts?.rejected ?? null}
					to="/app/explore/contributions"
				/>
			</section>

			<section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
				{roles.has("user") && (
					<ActionCard title="Ask" body="Run a query against the expert panel." to="/app/ask" />
				)}
				{roles.has("contributor") && (
					<ActionCard title="Contribute" body="Submit a signed claim." to="/app/contribute" />
				)}
				{roles.has("reviewer") && (
					<ActionCard title="Review" body="Vote on pending submissions." to="/app/review" />
				)}
				{roles.has("host") && (
					<ActionCard title="Host" body="Register your node and serve inference." to="/app/host" />
				)}
				<ActionCard
					title="Explore"
					body="Browse experts, contributions, and lineages."
					to="/app/explore/experts"
				/>
			</section>
		</div>
	);
}

function StatTile({
	label,
	value,
	to,
}: {
	label: string;
	value: number | null;
	to: "/app/explore/contributions";
}) {
	return (
		<Link
			to={to}
			className="border border-border bg-bg p-4 hover:border-border-strong hover:bg-bg-muted"
		>
			<div className="text-xs uppercase tracking-widest text-fg-subtle">{label}</div>
			<div className="mt-1 text-2xl font-bold tracking-tight">
				{value === null ? <Skeleton className="h-7 w-12" /> : value}
			</div>
		</Link>
	);
}

function ActionCard({
	title,
	body,
	to,
}: {
	title: string;
	body: string;
	to: "/app/ask" | "/app/contribute" | "/app/review" | "/app/host" | "/app/explore/experts";
}) {
	return (
		<Link to={to} className="block transition-colors hover:bg-bg-muted">
			<Card>
				<CardHeader title={title} />
				<p className="text-sm text-fg-muted">{body}</p>
			</Card>
		</Link>
	);
}
