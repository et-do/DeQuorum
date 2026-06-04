import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { NAV_LINKS, SITE_NAME } from "@/lib/env";

/**
 * Marketing top nav. Brand mark + the four marketing routes + a Launch
 * App CTA on the right. This nav does NOT appear inside /app — the app
 * has its own sidebar shell.
 */
export function TopNav() {
	return (
		<header className="sticky top-0 z-20 border-b border-border bg-bg/95 backdrop-blur supports-[backdrop-filter]:bg-bg/80">
			<Container wide className="flex h-14 items-center justify-between gap-6">
				<Link
					to="/"
					className="text-base font-bold tracking-wider"
					aria-label={`${SITE_NAME} home`}
				>
					{SITE_NAME.toUpperCase()}
				</Link>

				<nav
					aria-label="Primary"
					className="hidden items-center gap-6 text-xs uppercase tracking-widest text-fg-muted sm:flex"
				>
					{NAV_LINKS.filter((l) => l.to !== "/").map((link) => (
						<Link
							key={link.to}
							to={link.to}
							className="hover:text-fg"
							activeProps={{ className: "text-fg" }}
						>
							{link.label}
						</Link>
					))}
				</nav>

				<div className="flex items-center gap-3">
					<Link to="/app">
						<Button size="md">Launch App</Button>
					</Link>
					<ThemeToggle />
				</div>
			</Container>
		</header>
	);
}
