import { Link, useRouterState } from "@tanstack/react-router";
import { type ReactNode, useState } from "react";
import { ResizableSidebar } from "@/components/layout/ResizableSidebar";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { type Role, useRoles } from "@/lib/roles";

/**
 * App shell.
 *
 * Sidebar IA, organized by what the user is *here to do*, not by
 * what database tables exist. Every entry is purposeful for at least
 * one role; the four `explore/*` table viewers are folded behind a
 * single "Network" entry that lands on /app/explore.
 *
 *   - Ask        — chat with the network (every authed user)
 *   - Publish    — submit signed contributions (contributors)
 *   - Review     — triage/vote on pending submissions (reviewers)
 *   - Node       — host inference (hosts)
 *   - Network    — browse experts/contributions/contributors/categories
 *
 * Account + theme live in the sidebar footer so the rest of the
 * surface stays a focused workspace.
 *
 * No desktop top bar — the sidebar already carries the brand mark.
 * Mobile gets a slim header strip with the hamburger.
 */

interface NavItem {
	to: string;
	label: string;
	icon: string;
	/** Roles that this entry is FOR. Omit for items every authed user sees. */
	roles?: Role[];
	/** One-line description shown on hover or in the expanded form;
	 * makes the entry self-explanatory without needing a separate doc. */
	hint?: string;
}

const NAV_PRIMARY: NavItem[] = [
	{
		to: "/app/ask",
		label: "Ask",
		icon: "?",
		hint: "Chat with the network",
	},
	{
		to: "/app/contribute",
		label: "Publish",
		icon: "+",
		roles: ["contributor"],
		hint: "Submit a signed contribution",
	},
	{
		to: "/app/review",
		label: "Review",
		icon: "✓",
		roles: ["reviewer"],
		hint: "Triage and vote on pending submissions",
	},
	{
		to: "/app/host",
		label: "Host",
		icon: "◇",
		roles: ["host"],
		hint: "Run inference for the network",
	},
];

const NAV_SECONDARY: NavItem[] = [
	{
		to: "/app/explore",
		label: "Network",
		icon: "◯",
		hint: "Browse experts, contributions, contributors, categories",
	},
];

const NAV_FOOTER: NavItem[] = [{ to: "/app/account", label: "Settings", icon: "⚙" }];

export function AppShell({ children }: { children: ReactNode }) {
	const { roles } = useRoles();
	const { user } = useAuth();
	const [mobileOpen, setMobileOpen] = useState(false);
	const pathname = useRouterState({ select: (s) => s.location.pathname });

	const visible = (items: NavItem[]) =>
		items.filter((i) => !i.roles || i.roles.some((r) => roles.has(r)));

	const primary = visible(NAV_PRIMARY);
	const secondary = visible(NAV_SECONDARY);
	const footer = visible(NAV_FOOTER);

	const renderItem = (collapsed: boolean) => (item: NavItem) => {
		const active = item.to === "/app" ? pathname === "/app" : pathname.startsWith(item.to);
		return (
			<li key={item.to}>
				<Link
					to={item.to}
					onClick={() => setMobileOpen(false)}
					title={item.hint ?? item.label}
					className={cn(
						"flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
						collapsed && "justify-center px-2",
						active ? "bg-bg-muted text-fg" : "text-fg-muted hover:bg-bg-muted hover:text-fg",
					)}
				>
					<span aria-hidden="true" className="inline-block w-4 text-center text-xs">
						{item.icon}
					</span>
					{!collapsed && <span className="truncate">{item.label}</span>}
				</Link>
			</li>
		);
	};

	return (
		<div className="flex min-h-screen bg-bg text-fg">
			<ResizableSidebar
				id="app-nav"
				aria-label="App"
				mobileOpen={mobileOpen}
				onMobileClose={() => setMobileOpen(false)}
				defaultWidth={232}
				minWidth={200}
				maxWidth={320}
			>
				{({ collapsed, toggleCollapsed }) => (
					<>
						<div className="flex h-14 items-center justify-between px-3">
							<Link
								to="/app"
								onClick={() => setMobileOpen(false)}
								className="block min-w-0 truncate font-bold tracking-widest"
							>
								{collapsed ? "DQ" : "DEQUORUM"}
							</Link>
							{!collapsed && (
								<a
									href="/"
									className="text-xs uppercase tracking-widest text-fg-subtle hover:text-fg"
									title="Back to marketing site"
								>
									↗
								</a>
							)}
						</div>

						<nav className="flex-1 overflow-y-auto px-2 py-3">
							<ul className="space-y-0.5">{primary.map(renderItem(collapsed))}</ul>
							{secondary.length > 0 && (
								<>
									<div role="presentation" className="my-3 h-px bg-border/60" />
									<ul className="space-y-0.5">{secondary.map(renderItem(collapsed))}</ul>
								</>
							)}
						</nav>

						<div className="px-2 pb-2">
							<ul className="space-y-0.5">{footer.map(renderItem(collapsed))}</ul>
							<div
								className={cn(
									"mt-2 flex items-center gap-2 rounded-lg px-3 py-2",
									collapsed && "flex-col px-1",
								)}
							>
								{!collapsed && user && (
									<span
										className="min-w-0 flex-1 truncate text-xs text-fg-subtle"
										title={user.email ?? undefined}
									>
										{user.displayName ?? user.email ?? "Signed in"}
									</span>
								)}
								<ThemeToggle />
								<button
									type="button"
									onClick={toggleCollapsed}
									aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
									title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
									className="flex h-8 w-8 items-center justify-center rounded-md text-xs text-fg-subtle transition-colors hover:bg-bg-muted hover:text-fg"
								>
									{collapsed ? "›" : "‹"}
								</button>
							</div>
						</div>
					</>
				)}
			</ResizableSidebar>

			<div className="flex min-w-0 flex-1 flex-col">
				{/* Mobile-only header strip — desktop relies on the sidebar
				    brand mark + footer chrome and doesn't need a top bar. */}
				<header className="flex h-10 items-center bg-bg px-4 md:hidden">
					<button
						type="button"
						aria-label="Open menu"
						onClick={() => setMobileOpen(true)}
						className="text-fg-muted hover:text-fg"
					>
						☰
					</button>
				</header>
				<main className="flex-1 px-4 py-6 md:px-8 md:py-10">{children}</main>
			</div>
		</div>
	);
}
