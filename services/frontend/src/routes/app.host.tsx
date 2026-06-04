import { createFileRoute, Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ExternalLink } from "@/components/ui/Link";
import { PageHeader } from "@/components/ui/PageHeader";

export const Route = createFileRoute("/app/host")({
	component: HostRoute,
});

/**
 * Host section. Node registration + telemetry are still server-side TODOs
 * (no registry endpoint yet), so this is a placeholder explaining what the
 * flow will be and pointing at the local Ollama service that already runs.
 */
function HostRoute() {
	return (
		<div className="space-y-8">
			<PageHeader
				title="Host"
				description="Run an inference node, earn per token served."
				eyebrow={<Badge tone="warning">preview</Badge>}
			/>

			<EmptyState
				title="Node registration isn't live yet"
				description="The reference deployment has one Ollama node baked into compose. Multi-host federation is the next infrastructure milestone; this section will let you register your node and watch utilization once it ships."
				action={
					<ExternalLink
						href="https://github.com/et-do/dequorum/blob/main/docs/architecture/services-roadmap.md"
						target="_blank"
					>
						<Button variant="ghost">Roadmap</Button>
					</ExternalLink>
				}
			/>

			<Card>
				<CardHeader title="Local Ollama" subtitle="dev only" />
				<dl className="grid grid-cols-2 gap-3 text-sm">
					<dt className="text-fg-subtle">Endpoint</dt>
					<dd className="text-fg">http://ollama:11434</dd>
					<dt className="text-fg-subtle">Default model</dt>
					<dd className="text-fg">qwen2.5-coder:7b</dd>
					<dt className="text-fg-subtle">Logs</dt>
					<dd>
						<Link to="/app/account" className="text-fg underline-offset-4 hover:underline">
							docker compose logs ollama
						</Link>
					</dd>
				</dl>
			</Card>
		</div>
	);
}
