import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/lib/auth";
import { ALL_ROLES, type Role, useRoles } from "@/lib/roles";
import { useTheme } from "@/lib/theme";
import { useToasts } from "@/lib/toasts";

export const Route = createFileRoute("/app/account")({
	component: AccountRoute,
});

function AccountRoute() {
	const navigate = useNavigate();
	const { user, signOut: fbSignOut } = useAuth();
	const { roles, set: setRoles, clear: clearRoles } = useRoles();
	const { theme, setTheme } = useTheme();
	const { toast } = useToasts();

	function toggleRole(r: Role) {
		const next = new Set(roles);
		if (next.has(r)) next.delete(r);
		else next.add(r);
		setRoles(next);
		toast(`Roles updated · ${next.size} active`, { tone: "success" });
	}

	async function signOut() {
		await fbSignOut();
		clearRoles();
		navigate({ to: "/" });
	}

	return (
		<div className="mx-auto max-w-3xl space-y-8">
			<PageHeader title="Account" />

			<Card>
				<CardHeader title="Identity" />
				<div className="flex items-center gap-4">
					<Avatar seed={user?.uid ?? "anon"} size={48} />
					<div className="min-w-0 flex-1">
						<div className="font-bold tracking-tight">
							{user?.displayName || user?.email || "—"}
						</div>
						<div className="truncate text-xs uppercase tracking-widest text-fg-subtle">
							{user?.uid}
						</div>
					</div>
				</div>
			</Card>

			<Card>
				<CardHeader
					title="Roles"
					subtitle="what shows up in the sidebar"
					actions={<Badge tone="muted">{roles.size} active</Badge>}
				/>
				<ul className="grid gap-3 sm:grid-cols-2">
					{ALL_ROLES.map((r) => {
						const active = roles.has(r.id);
						return (
							<li key={r.id}>
								<button
									type="button"
									aria-pressed={active}
									onClick={() => toggleRole(r.id)}
									className={`w-full border p-3 text-left ${
										active
											? "border-fg bg-fg text-bg"
											: "border-border bg-bg hover:border-border-strong"
									}`}
								>
									<div className="font-bold tracking-tight">{r.label}</div>
									<div className={`mt-1 text-xs ${active ? "text-bg/80" : "text-fg-muted"}`}>
										{r.blurb}
									</div>
								</button>
							</li>
						);
					})}
				</ul>
			</Card>

			<Card>
				<CardHeader title="Theme" />
				<div className="flex gap-2">
					<Button
						variant={theme === "light" ? "primary" : "ghost"}
						onClick={() => setTheme("light")}
					>
						Light
					</Button>
					<Button variant={theme === "dark" ? "primary" : "ghost"} onClick={() => setTheme("dark")}>
						Dark
					</Button>
				</div>
			</Card>

			{user && (
				<Card>
					<CardHeader title="Sign out" subtitle="ends your current session" />
					<Button variant="ghost" onClick={signOut}>
						Sign out
					</Button>
				</Card>
			)}
		</div>
	);
}
