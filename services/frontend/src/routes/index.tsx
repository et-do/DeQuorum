import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { NetworkVisualization } from "@/components/marketing/NetworkVisualization";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { APP_PATH } from "@/lib/env";

export const Route = createFileRoute("/")({
	component: HomePage,
});

function HomePage() {
	const navigate = useNavigate();

	return (
		<Container wide className="flex flex-col items-center pb-20 pt-10 sm:pt-16">
			<h1 className="max-w-4xl text-center text-4xl font-bold leading-[1.05] tracking-tight sm:text-6xl md:text-7xl">
				The AI commons.
			</h1>
			<p className="mt-5 max-w-xl text-center text-sm text-fg-muted sm:text-base">
				Owned by the humans who built it. Every answer cited, every cited human paid.
			</p>

			<div className="relative mt-10 aspect-square w-full max-w-[680px]">
				<NetworkVisualization />
			</div>

			<Button size="lg" className="mt-6" onClick={() => navigate({ to: APP_PATH })}>
				Launch App
			</Button>
		</Container>
	);
}
