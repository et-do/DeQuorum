import { Link, useRouterState } from "@tanstack/react-router";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useAuth } from "@/lib/auth";
import { NAV_LINKS, SITE_NAME } from "@/lib/env";

/**
 * Marketing top nav. Brand mark + the four marketing routes + a CTA
 * on the right. This nav does NOT appear inside /app — the app has its
 * own sidebar shell.
 *
 * The right-hand chrome reflects auth state:
 *   - Signed out  → "Sign in" link + "Launch App" CTA (lands on /signin
 *                   if not signed in by the time they click; today the
 *                   app routes still load read-only so the CTA is more
 *                   "enter the app" than "force auth").
 *   - Signed in   → small Avatar + display name + "Launch App" CTA that
 *                   goes straight to /app/ask.
 *
 * On the landing page (`/`) the Launch App CTA is suppressed because
 * the hero already carries a prominent button; two CTAs compete.
 */
export function TopNav() {
	const pathname = useRouterState({ select: (s) => s.location.pathname });
	const onLanding = pathname === "/";
	const { user, ready } = useAuth();

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
					{!onLanding && (
						<Link to="/app">
							<Button size="md">Launch App</Button>
						</Link>
					)}
					{ready &&
						(user ? (
							<Link
								to="/app/account"
								className="hidden items-center gap-2 text-xs uppercase tracking-widest text-fg-muted hover:text-fg sm:flex"
								title="Account"
							>
								<Avatar seed={user.uid} size={22} />
								<span className="hidden max-w-[10rem] truncate md:inline">
									{user.displayName ?? user.email ?? "Account"}
								</span>
							</Link>
						) : (
							<Link
								to="/signin"
								className="hidden text-xs uppercase tracking-widest text-fg-muted hover:text-fg sm:inline"
							>
								Sign in
							</Link>
						))}
					<ThemeToggle />
				</div>
			</Container>
		</header>
	);
}
