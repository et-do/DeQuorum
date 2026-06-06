import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { NetworkVisualization } from "@/components/marketing/NetworkVisualization";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { useAuth } from "@/lib/auth";
import { APP_PATH } from "@/lib/env";

export const Route = createFileRoute("/")({
	component: HomePage,
});

function HomePage() {
	const navigate = useNavigate();
	const { user, ready } = useAuth();
	const signedIn = ready && !!user;

	return (
		<Container wide className="flex flex-col items-center pb-20 pt-10 sm:pt-16">
			<h1 className="max-w-4xl text-center text-2xl font-bold leading-[1.05] tracking-tight sm:text-4xl md:text-5lets xsl">
				AI by the people, for the people.
			</h1>
			<p className="mt-5 max-w-xl text-center text-sm text-fg-muted sm:text-base">
				Humans created all content for AI, its time they get the recognition, ownership, and
				kickbacks from it.
			</p>
			{/* Mobile: compact square. Desktop: wide landscape box so the
			    four corner labels spread to the edges and frame the mesh
			    instead of crowding it. The canvas auto-centers the sphere
			    and sizes it to the box's shorter side, so the mesh itself
			    stays small while the labels fan out. */}
			<div className="relative mt-8 aspect-square w-full max-w-[440px] sm:aspect-auto sm:h-[400px] sm:max-w-[820px]">
				<NetworkVisualization />
			</div>

			<div className="mt-6 flex flex-col items-center gap-3">
				<Button size="lg" onClick={() => navigate({ to: APP_PATH })}>
					{signedIn ? "Continue to app" : "Launch app"}
				</Button>
				{!signedIn && (
					<Link
						to="/signin"
						className="text-xs uppercase tracking-widest text-fg-muted underline-offset-4 hover:text-fg hover:underline"
					>
						Sign in →
					</Link>
				)}
			</div>
			{signedIn && (
				<p className="mt-4 text-[11px] uppercase tracking-widest text-fg-subtle">
					Signed in as {user?.displayName ?? user?.email}
				</p>
			)}
		</Container>
	);
}
