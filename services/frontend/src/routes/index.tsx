import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { NetworkMesh } from "@/components/marketing/NetworkMesh";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { APP_PATH } from "@/lib/env";

export const Route = createFileRoute("/")({
	component: HomePage,
});

function HomePage() {
	const navigate = useNavigate();

	return (
		<Container wide className="flex flex-col items-center pb-24 pt-12 sm:pt-16">
			<div className="aspect-square w-full max-w-[640px]">
				<NetworkMesh />
			</div>

			<div className="mt-6 flex flex-col items-center gap-6 text-center">
				<p className="max-w-md text-sm text-fg-muted">
					A signed AI network. Contributors publish knowledge. Reviewers vote. Node hosters serve
					answers.
				</p>
				<Button size="lg" onClick={() => navigate({ to: APP_PATH })}>
					Launch App
				</Button>
			</div>
		</Container>
	);
}
