import { createFileRoute } from "@tanstack/react-router";
import { Container } from "@/components/ui/Container";

export const Route = createFileRoute("/about")({
	component: AboutPage,
});

function AboutPage() {
	return (
		<Container className="space-y-6 py-16 sm:py-24">
			<h1 className="text-3xl font-bold tracking-tight sm:text-4xl">About</h1>

			<p className="text-fg-muted">
				DeQuorum is a crowdsourced AI platform owned by the people who make it work. Contributors
				publish the knowledge. Reviewers decide what holds up. Node hosters provide the compute. End
				users ask questions. Every role earns when the network is used.
			</p>

			<p className="text-fg-muted">
				No BigTech, no closed model, no rent extraction. The network is the commons. Identity,
				signatures, and payouts are public and auditable end-to-end. If your knowledge or your
				hardware powers an answer, you get credit and you get paid.
			</p>
		</Container>
	);
}
