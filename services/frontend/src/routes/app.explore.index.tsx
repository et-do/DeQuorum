import { createFileRoute, Link } from "@tanstack/react-router";

/**
 * /app/explore is the "browse the network" landing page.
 *
 * The three sub-surfaces below were each top-level sidebar entries in
 * the old IA. Folding them behind one "Network" entry makes the
 * primary nav role-purposeful (Ask / Publish / Review / Node) instead
 * of a database-table tour. The sub-pages still work via direct URLs.
 */
export const Route = createFileRoute("/app/explore/")({
	component: ExploreLanding,
});

const TILES = [
	{
		to: "/app/explore/contributions" as const,
		title: "Contributions",
		body: "Every signed claim in the network. Filter by status, category, or contributor.",
		icon: "≡",
	},
	{
		to: "/app/explore/contributors" as const,
		title: "Contributors",
		body: "The people behind the knowledge. Their tier, their submissions, their voting history.",
		icon: "@",
	},
	{
		to: "/app/explore/categories" as const,
		title: "Categories",
		body: "The taxonomy. Every contribution lives in a category; routable leaves carry a persona.",
		icon: "#",
	},
];

function ExploreLanding() {
	return (
		<div className="mx-auto max-w-4xl space-y-8">
			<header className="space-y-2">
				<h1 className="text-2xl font-bold tracking-tight">Network</h1>
				<p className="text-sm text-fg-muted">
					Everything the network knows, and everyone who put it there.
				</p>
			</header>

			<ul className="grid gap-3 sm:grid-cols-2">
				{TILES.map((t) => (
					<li key={t.to}>
						<Link
							to={t.to}
							className="group flex h-full flex-col gap-2 rounded-2xl bg-bg-elevated p-5 ring-1 ring-border transition-colors hover:ring-fg-muted"
						>
							<div className="flex items-center gap-3">
								<span
									aria-hidden="true"
									className="flex h-8 w-8 items-center justify-center rounded-full bg-bg-muted text-sm font-bold tracking-widest text-fg-muted group-hover:text-fg"
								>
									{t.icon}
								</span>
								<h2 className="text-base font-bold tracking-tight">{t.title}</h2>
							</div>
							<p className="text-sm text-fg-muted">{t.body}</p>
						</Link>
					</li>
				))}
			</ul>
		</div>
	);
}
