import { Link, useRouterState } from "@tanstack/react-router";
import { type ReactNode, useState } from "react";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { cn } from "@/lib/cn";
import { type Role, useRoles } from "@/lib/roles";

/**
 * App shell: persistent left sidebar + main content area. Sidebar items
 * are role-gated via the optional `roles` predicate; everyone sees
 * Dashboard, Explore, and Account.
 *
 * On screens narrower than `md` (768px), the sidebar collapses behind a
 * hamburger button to keep the content area usable on mobile.
 */

interface NavItem {
	to: string;
	label: string;
	/** When set, only show if the user has at least one of these roles. */
	roles?: Role[];
	/** Section header above this group. */
	group?: string;
}

const NAV: NavItem[] = [
	{ group: "OVERVIEW", to: "/app", label: "Dashboard" },

	{ group: "MY WORK", to: "/app/ask", label: "Ask", roles: ["user"] },
	{
		group: "MY WORK",
		to: "/app/contribute",
		label: "Contribute",
		roles: ["contributor"],
	},
	{
		group: "MY WORK",
		to: "/app/review",
		label: "Review",
		roles: ["reviewer"],
	},
	{ group: "MY WORK", to: "/app/host", label: "Host", roles: ["host"] },

	{ group: "EXPLORE", to: "/app/explore/experts", label: "Experts" },
	{
		group: "EXPLORE",
		to: "/app/explore/contributions",
		label: "Contributions",
	},
	{
		group: "EXPLORE",
		to: "/app/explore/contributors",
		label: "Contributors",
	},
	{ group: "EXPLORE", to: "/app/explore/categories", label: "Categories" },

	{ group: "ACCOUNT", to: "/app/account", label: "Settings" },
];

export function AppShell({ children }: { children: ReactNode }) {
	const { roles } = useRoles();
	const [mobileOpen, setMobileOpen] = useState(false);
	const matches = useRouterState({ select: (s) => s.location.pathname });

	const visible = NAV.filter((item) => !item.roles || item.roles.some((r) => roles.has(r)));
	const groups = Array.from(new Set(visible.map((i) => i.group ?? "")));

	return (
		<div className="flex min-h-screen bg-bg text-fg">
			{/* Sidebar */}
			<aside
				aria-label="App"
				className={cn(
					"fixed inset-y-0 left-0 z-40 w-64 transform border-r border-border bg-bg-elevated transition-transform md:relative md:translate-x-0",
					mobileOpen ? "translate-x-0" : "-translate-x-full",
				)}
			>
				<div className="flex h-14 items-center justify-between border-b border-border px-4">
					<Link
						to="/app"
						onClick={() => setMobileOpen(false)}
						className="font-bold tracking-widest"
					>
						DEQUORUM
					</Link>
					<a
						href="/"
						className="text-xs uppercase tracking-widest text-fg-subtle hover:text-fg"
						title="Back to marketing site"
					>
						↗
					</a>
				</div>

				<nav className="space-y-6 px-2 py-4">
					{groups.map((g) => (
						<div key={g}>
							{g && (
								<div className="px-3 pb-2 text-xs uppercase tracking-widest text-fg-subtle">
									{g}
								</div>
							)}
							<ul className="space-y-1">
								{visible
									.filter((i) => (i.group ?? "") === g)
									.map((item) => {
										const active =
											item.to === "/app" ? matches === "/app" : matches.startsWith(item.to);
										return (
											<li key={item.to}>
												<Link
													to={item.to}
													onClick={() => setMobileOpen(false)}
													className={cn(
														"block px-3 py-2 text-sm",
														active
															? "bg-fg text-bg"
															: "text-fg-muted hover:bg-bg-muted hover:text-fg",
													)}
												>
													{item.label}
												</Link>
											</li>
										);
									})}
							</ul>
						</div>
					))}
				</nav>
			</aside>

			{/* Mobile backdrop */}
			{mobileOpen && (
				<button
					type="button"
					aria-label="Close menu"
					onClick={() => setMobileOpen(false)}
					className="fixed inset-0 z-30 bg-bg/70 backdrop-blur-sm md:hidden"
				/>
			)}

			{/* Main */}
			<div className="flex min-w-0 flex-1 flex-col">
				<header className="flex h-14 items-center justify-between border-b border-border bg-bg px-4 md:px-6">
					<button
						type="button"
						aria-label="Open menu"
						onClick={() => setMobileOpen(true)}
						className="md:hidden"
					>
						☰
					</button>
					<div />
					<ThemeToggle />
				</header>
				<main className="flex-1 px-4 py-6 md:px-8 md:py-10">{children}</main>
			</div>
		</div>
	);
}
