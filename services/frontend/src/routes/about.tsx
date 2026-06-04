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
				DeQuorum is a small AI network you can run yourself. Contributors publish knowledge under a
				signed identity. Reviewers vote on what holds up. Node hosters provide inference. End users
				ask questions and see who their answer came from.
			</p>

			<p className="text-fg-muted">
				It's Apache-2.0 and the reference deployment is one person on nights and weekends. The goal
				isn't to replace any of the frontier APIs. It's to make a usable shape for AI infrastructure
				where the people whose work goes in are visible — and paid — at the other end.
			</p>
		</Container>
	);
}
