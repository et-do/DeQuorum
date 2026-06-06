import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { useToasts } from "@/lib/toasts";

/**
 * Email/password + Google sign-in panel. Works against the local
 * Firebase emulator in dev (the auth module connects automatically).
 *
 * Mode toggle switches between sign-in and sign-up. Errors surface via
 * toast + inline message so neither path is silent.
 */
export function SignInPanel({ className }: { className?: string }) {
	const { signInEmail, signUpEmail, signInGoogle } = useAuth();
	const { toast } = useToasts();
	const [mode, setMode] = useState<"signin" | "signup">("signin");
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [displayName, setDisplayName] = useState("");
	const [busy, setBusy] = useState(false);
	const [error, setError] = useState<string | null>(null);

	async function onSubmit(e: FormEvent<HTMLFormElement>) {
		e.preventDefault();
		setError(null);
		setBusy(true);
		try {
			if (mode === "signin") await signInEmail(email, password);
			else await signUpEmail(email, password, displayName.trim() || undefined);
			toast(mode === "signin" ? "Signed in" : "Account created", { tone: "success" });
		} catch (e) {
			const msg = e instanceof Error ? e.message : String(e);
			setError(prettyFirebaseError(msg));
		} finally {
			setBusy(false);
		}
	}

	async function onGoogle() {
		setError(null);
		setBusy(true);
		try {
			await signInGoogle();
		} catch (e) {
			const msg = e instanceof Error ? e.message : String(e);
			setError(prettyFirebaseError(msg));
		} finally {
			setBusy(false);
		}
	}

	return (
		<Card className={cn("space-y-5", className)}>
			<CardHeader
				title={mode === "signin" ? "Sign in" : "Create an account"}
				subtitle={
					mode === "signin"
						? "Use your DeQuorum credentials"
						: "Email + password is fine; emulator-friendly"
				}
				actions={
					<button
						type="button"
						onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
						className="text-xs uppercase tracking-widest text-fg-subtle hover:text-fg"
					>
						{mode === "signin" ? "Sign up →" : "← Sign in"}
					</button>
				}
			/>

			<form onSubmit={onSubmit} className="space-y-3">
				{mode === "signup" && (
					<div>
						<label className="block text-xs uppercase tracking-widest text-fg-subtle">
							Display name
						</label>
						<input
							value={displayName}
							onChange={(e) => setDisplayName(e.target.value)}
							className="mt-1 w-full border border-border bg-bg px-3 py-2 text-fg focus:border-border-strong focus:outline-none"
						/>
					</div>
				)}
				<div>
					<label className="block text-xs uppercase tracking-widest text-fg-subtle">Email</label>
					<input
						type="email"
						value={email}
						onChange={(e) => setEmail(e.target.value)}
						required
						autoComplete="email"
						className="mt-1 w-full border border-border bg-bg px-3 py-2 text-fg focus:border-border-strong focus:outline-none"
					/>
				</div>
				<div>
					<label className="block text-xs uppercase tracking-widest text-fg-subtle">Password</label>
					<input
						type="password"
						value={password}
						onChange={(e) => setPassword(e.target.value)}
						required
						minLength={6}
						autoComplete={mode === "signin" ? "current-password" : "new-password"}
						className="mt-1 w-full border border-border bg-bg px-3 py-2 text-fg focus:border-border-strong focus:outline-none"
					/>
				</div>

				{error && <p className="text-sm text-fg-muted">{error}</p>}

				<Button type="submit" size="md" disabled={busy} className="w-full">
					{busy ? "…" : mode === "signin" ? "Sign in" : "Create account"}
				</Button>
			</form>

			<div className="flex items-center gap-3">
				<div className="h-px flex-1 bg-border" />
				<span className="text-xs uppercase tracking-widest text-fg-subtle">or</span>
				<div className="h-px flex-1 bg-border" />
			</div>

			<Button
				type="button"
				variant="ghost"
				size="md"
				onClick={onGoogle}
				disabled={busy}
				className="w-full"
			>
				Continue with Google
			</Button>
		</Card>
	);
}

function prettyFirebaseError(msg: string): string {
	if (msg.includes("invalid-credential")) return "Email or password is wrong";
	if (msg.includes("email-already-in-use")) return "That email already has an account";
	if (msg.includes("weak-password")) return "Password must be at least 6 characters";
	if (msg.includes("invalid-email")) return "Email doesn't look right";
	return msg.replace(/^Firebase:\s*/i, "");
}
