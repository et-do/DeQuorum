import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { SignInPanel } from "@/components/auth/SignInPanel";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { Stepper } from "@/components/ui/Stepper";
import { useAuth } from "@/lib/auth";
import { ALL_ROLES, type Role, useRoles } from "@/lib/roles";
import { useToasts } from "@/lib/toasts";

/**
 * Single onboarding flow:
 *
 *   1  Welcome    — what the network is, what you'll set up
 *   2  Sign in    — Firebase Auth (email/password or Google).
 *                   Auth state advances the step automatically once a
 *                   user is present.
 *   3  Roles      — pick what you want to do; persists to localStorage
 *                   (server-side role storage comes when contributor
 *                   profiles ship).
 *   4  Done       — straight to the dashboard.
 *
 * The wizard lives outside the app shell so unauthenticated users hit it
 * directly without app chrome distractions.
 */
export const Route = createFileRoute("/onboarding")({
	component: OnboardingWizard,
});

const STEPS = [{ label: "Welcome" }, { label: "Sign in" }, { label: "Roles" }] as const;

function OnboardingWizard() {
	const navigate = useNavigate();
	const { user, ready: authReady } = useAuth();
	const { set: setRolesValue, roles } = useRoles();
	const { toast } = useToasts();

	const [step, setStep] = useState(0);
	const [selected, setSelected] = useState<Set<Role>>(new Set(roles));

	// Once Firebase auth completes, jump past the sign-in step.
	useEffect(() => {
		if (!authReady) return;
		if (user && step <= 1) setStep(2);
	}, [user, authReady, step]);

	function toggleRole(r: Role) {
		setSelected((prev) => {
			const next = new Set(prev);
			if (next.has(r)) next.delete(r);
			else next.add(r);
			return next;
		});
	}

	function finish() {
		setRolesValue(selected);
		toast("Welcome aboard", { tone: "success" });
		navigate({ to: "/app" });
	}

	return (
		<Container className="py-12 sm:py-16">
			<Stepper steps={[...STEPS]} current={step} className="mb-10" />

			{step === 0 && (
				<section className="space-y-6">
					<h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Welcome to DeQuorum</h1>
					<p className="text-fg-muted">
						DeQuorum is a crowdsourced AI platform owned by the people who make it work. This setup
						takes about a minute — you sign in, pick what you want to do, and you're in.
					</p>
					<Button size="lg" onClick={() => setStep(1)}>
						Get started
					</Button>
				</section>
			)}

			{step === 1 && !user && (
				<section className="space-y-6">
					<header className="space-y-2">
						<h1 className="text-2xl font-bold tracking-tight">Create an account or sign in</h1>
						<p className="text-fg-muted">
							Your sessions, contributions, and earnings live under this account.
						</p>
					</header>
					<div className="mx-auto max-w-md">
						<SignInPanel />
					</div>
					<div className="flex justify-start">
						<Button variant="ghost" onClick={() => setStep(0)}>
							Back
						</Button>
					</div>
				</section>
			)}

			{step === 2 && (
				<section className="space-y-6">
					<header className="space-y-2">
						<h1 className="text-2xl font-bold tracking-tight">What do you want to do?</h1>
						<p className="text-fg-muted">Pick one or more. You can change this later in Account.</p>
					</header>
					<ul className="grid gap-3 sm:grid-cols-2">
						{ALL_ROLES.map((r) => {
							const active = selected.has(r.id);
							return (
								<li key={r.id}>
									<button
										type="button"
										onClick={() => toggleRole(r.id)}
										aria-pressed={active}
										className={`w-full border p-4 text-left transition-colors ${
											active
												? "border-fg bg-fg text-bg"
												: "border-border bg-bg text-fg hover:border-border-strong hover:bg-bg-muted"
										}`}
									>
										<div className="font-bold tracking-tight">{r.label}</div>
										<div className={`mt-1 text-sm ${active ? "text-bg/80" : "text-fg-muted"}`}>
											{r.blurb}
										</div>
									</button>
								</li>
							);
						})}
					</ul>
					<div className="flex justify-between">
						<Button variant="ghost" onClick={() => setStep(1)}>
							Back
						</Button>
						<Button size="lg" onClick={finish} disabled={selected.size === 0}>
							Finish
						</Button>
					</div>
				</section>
			)}
		</Container>
	);
}
