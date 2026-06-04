import { createFileRoute } from "@tanstack/react-router";
import { Container } from "@/components/ui/Container";
import { ExternalLink } from "@/components/ui/Link";

export const Route = createFileRoute("/pricing")({
	component: PricingPage,
});

function PricingPage() {
	return (
		<Container wide className="py-16 sm:py-24">
			<header className="mx-auto max-w-2xl space-y-2 text-center">
				<h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Pricing</h1>
				<p className="text-fg-muted">Three roles in the loop. Each one earns when a query runs.</p>
			</header>

			<div className="mt-16 grid gap-px border border-border bg-border md:grid-cols-3">
				<RoleCard
					role="End user"
					price="$10 / month"
					detail="Roughly $0.02 per query at typical usage. Buys cited, voted answers from a panel of experts."
				/>
				<RoleCard
					role="Contributor"
					price="$1.30 / accepted"
					detail="Per submission that clears review. Active contributors with high-cite knowledge can reach $50–$100/month."
				/>
				<RoleCard
					role="Node hoster"
					price="~$50 / month"
					detail="Per node running an Ollama-compatible inference endpoint. Covers consumer-GPU electricity and partial amortization."
				/>
			</div>

			<section className="mx-auto mt-12 max-w-2xl space-y-3 text-sm text-fg-muted">
				<p>
					Numbers assume 1,000 active users (800 end users, 150 contributors, 50 node hosters) at
					~20 queries/day/user. Sensitivity analysis and the failure modes live in{" "}
					<ExternalLink
						href="https://github.com/et-do/dequorum/blob/main/docs/architecture/cost-model.md"
						target="_blank"
					>
						cost-model.md
					</ExternalLink>
					.
				</p>
			</section>
		</Container>
	);
}

function RoleCard({ role, price, detail }: { role: string; price: string; detail: string }) {
	return (
		<div className="space-y-3 bg-bg p-6">
			<div className="text-xs uppercase tracking-widest text-fg-subtle">{role}</div>
			<div className="text-2xl font-bold tracking-tight text-fg">{price}</div>
			<p className="text-sm text-fg-muted">{detail}</p>
		</div>
	);
}
