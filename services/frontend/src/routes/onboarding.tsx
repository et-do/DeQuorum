import { useMutation, useQuery } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { Stepper } from "@/components/ui/Stepper";
import { useAccount } from "@/lib/account";
import { createContributor, getAgreement } from "@/lib/api";
import { ALL_ROLES, type Role, useRoles } from "@/lib/roles";
import { useToasts } from "@/lib/toasts";

/**
 * Onboarding wizard. Lives at the top level (not under /app) so users
 * arriving from the marketing CTA don't see app chrome around it.
 *
 * Steps:
 *   1 Welcome — what the network is and what they'll set up
 *   2 Roles  — multi-select (one or more required)
 *   3 Profile — display name + optional email
 *   4 Keypair — sign the agreement, generate a keypair, reveal once
 */
export const Route = createFileRoute("/onboarding")({
	component: OnboardingWizard,
});

const STEPS = [{ label: "Welcome" }, { label: "Roles" }, { label: "Profile" }, { label: "Keys" }];

function OnboardingWizard() {
	const navigate = useNavigate();
	const { toast } = useToasts();
	const { set: setRolesValue } = useRoles();
	const { setAccount } = useAccount();
	const agreement = useQuery({
		queryKey: ["agreement"],
		queryFn: getAgreement,
	});

	const [step, setStep] = useState(0);
	const [selected, setSelected] = useState<Set<Role>>(new Set());
	const [displayName, setDisplayName] = useState("");
	const [email, setEmail] = useState("");
	const [created, setCreated] = useState<{
		contributor_id: string;
		display_name: string;
		public_key_hex: string;
		private_key_hex: string;
	} | null>(null);

	const create = useMutation({
		mutationFn: createContributor,
		onSuccess: (res) => {
			setCreated({
				contributor_id: res.contributor_id,
				display_name: res.display_name,
				public_key_hex: res.public_key_hex,
				private_key_hex: res.private_key_hex,
			});
			setAccount({
				contributor_id: res.contributor_id,
				display_name: res.display_name,
				public_key_hex: res.public_key_hex,
			});
			setRolesValue(selected);
			toast("Account created", { tone: "success" });
		},
		onError: (err: Error) => toast(err.message, { tone: "error", durationMs: 8000 }),
	});

	function toggleRole(r: Role) {
		setSelected((prev) => {
			const next = new Set(prev);
			if (next.has(r)) next.delete(r);
			else next.add(r);
			return next;
		});
	}

	function onProfileSubmit(e: FormEvent<HTMLFormElement>) {
		e.preventDefault();
		if (!displayName.trim()) return;
		setStep(3);
		create.mutate({
			display_name: displayName.trim(),
			email: email.trim() || undefined,
		});
	}

	return (
		<Container className="py-12 sm:py-16">
			<Stepper steps={STEPS} current={step} className="mb-10" />

			{step === 0 && (
				<section className="space-y-6">
					<h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Welcome to DeQuorum</h1>
					<p className="text-fg-muted">
						This is the setup flow for a new account. You'll pick what you want to do on the
						network, choose a display name, and walk away with a signing keypair. Takes about a
						minute.
					</p>
					<div className="flex gap-3">
						<Button size="lg" onClick={() => setStep(1)}>
							Get started
						</Button>
					</div>
				</section>
			)}

			{step === 1 && (
				<section className="space-y-6">
					<header className="space-y-2">
						<h1 className="text-2xl font-bold tracking-tight">What do you want to do?</h1>
						<p className="text-fg-muted">Pick one or more. You can change this later.</p>
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
						<Button variant="ghost" onClick={() => setStep(0)}>
							Back
						</Button>
						<Button onClick={() => setStep(2)} disabled={selected.size === 0}>
							Continue
						</Button>
					</div>
				</section>
			)}

			{step === 2 && (
				<form className="space-y-6" onSubmit={onProfileSubmit}>
					<header className="space-y-2">
						<h1 className="text-2xl font-bold tracking-tight">Profile</h1>
						<p className="text-fg-muted">
							The display name is public. Email is optional and hashed locally for tier upgrades.
						</p>
					</header>
					<div className="space-y-4">
						<div>
							<label className="block text-xs uppercase tracking-widest text-fg-subtle">
								Display name
							</label>
							<input
								value={displayName}
								onChange={(e) => setDisplayName(e.target.value)}
								required
								autoFocus
								className="mt-1 w-full border border-border bg-bg px-3 py-2 text-fg focus:border-border-strong focus:outline-none"
							/>
						</div>
						<div>
							<label className="block text-xs uppercase tracking-widest text-fg-subtle">
								Email <span className="normal-case text-fg-muted">(optional)</span>
							</label>
							<input
								type="email"
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								className="mt-1 w-full border border-border bg-bg px-3 py-2 text-fg focus:border-border-strong focus:outline-none"
							/>
						</div>
						{agreement.data && (
							<details className="border border-border bg-bg p-4">
								<summary className="cursor-pointer text-xs uppercase tracking-widest text-fg-subtle">
									Agreement v{agreement.data.version} (signed on completion)
								</summary>
								<pre className="mt-3 max-h-60 overflow-auto whitespace-pre-wrap text-sm text-fg-muted">
									{agreement.data.text}
								</pre>
							</details>
						)}
					</div>
					<div className="flex justify-between">
						<Button variant="ghost" onClick={() => setStep(1)}>
							Back
						</Button>
						<Button type="submit" disabled={create.isPending}>
							{create.isPending ? "Creating…" : "Create account"}
						</Button>
					</div>
				</form>
			)}

			{step === 3 && (
				<section className="space-y-6">
					{create.isPending && <p className="text-fg-muted">Generating keypair…</p>}
					{create.isError && <p className="text-fg-muted">{(create.error as Error).message}</p>}
					{created && (
						<>
							<header className="space-y-2">
								<h1 className="text-2xl font-bold tracking-tight">Save your private key</h1>
								<p className="text-fg-muted">
									This is the only time you'll see this. Save it somewhere safe. The network can't
									recover it.
								</p>
							</header>
							<div className="space-y-3">
								<KeyLine label="Contributor ID" value={created.contributor_id} />
								<KeyLine label="Public key" value={created.public_key_hex} />
								<KeyLine label="Private key" value={created.private_key_hex} danger />
							</div>
							<Button size="lg" onClick={() => navigate({ to: "/app" })}>
								I saved it — go to dashboard
							</Button>
						</>
					)}
				</section>
			)}
		</Container>
	);
}

function KeyLine({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
	return (
		<div className="space-y-1">
			<div className="flex items-center justify-between text-xs uppercase tracking-widest text-fg-subtle">
				<span>{label}</span>
				<button
					type="button"
					onClick={() => navigator.clipboard.writeText(value)}
					className="hover:text-fg"
				>
					Copy
				</button>
			</div>
			<pre
				className={`overflow-x-auto border p-2 text-sm ${
					danger ? "border-fg bg-bg-muted text-fg" : "border-border bg-bg text-fg"
				}`}
			>
				{value}
			</pre>
		</div>
	);
}
