import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAccount } from "@/lib/account";
import { ALL_ROLES, type Role, useRoles } from "@/lib/roles";
import { useTheme } from "@/lib/theme";
import { useToasts } from "@/lib/toasts";

export const Route = createFileRoute("/app/account")({
	component: AccountRoute,
});

function AccountRoute() {
	const navigate = useNavigate();
	const { account, clear: clearAccount } = useAccount();
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

	function signOut() {
		clearAccount();
		clearRoles();
		navigate({ to: "/" });
	}

	return (
		<div className="mx-auto max-w-3xl space-y-8">
			<PageHeader title="Account" />

			<Card>
				<CardHeader title="Identity" subtitle="local profile" />
				{!account ? (
					<EmptyState
						title="No local account"
						description="Run the onboarding flow to generate a keypair."
						action={<Button onClick={() => navigate({ to: "/onboarding" })}>Onboarding</Button>}
					/>
				) : (
					<div className="flex items-center gap-4">
						<Avatar seed={account.contributor_id} size={48} />
						<div>
							<div className="font-bold tracking-tight">{account.display_name}</div>
							<div className="text-xs uppercase tracking-widest text-fg-subtle">
								{account.contributor_id}
							</div>
						</div>
					</div>
				)}
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

			{account && (
				<Card>
					<CardHeader title="Sign out" subtitle="clears local account + roles" />
					<Button variant="ghost" onClick={signOut}>
						Sign out
					</Button>
				</Card>
			)}
		</div>
	);
}
