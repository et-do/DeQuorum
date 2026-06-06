import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { SignInPanel } from "@/components/auth/SignInPanel";
import { Container } from "@/components/ui/Container";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/signin")({
	component: SignIn,
});

function SignIn() {
	const navigate = useNavigate();
	const { user, ready } = useAuth();

	useEffect(() => {
		if (ready && user) {
			navigate({ to: "/app" });
		}
	}, [ready, user, navigate]);

	return (
		<Container className="py-16">
			<div className="mx-auto max-w-md space-y-6">
				<header className="space-y-2 text-center">
					<h1 className="text-2xl font-bold tracking-tight">Sign in to DeQuorum</h1>
					<p className="text-sm text-fg-muted">
						Your sessions and contributions live under your account.
					</p>
				</header>
				<SignInPanel />
			</div>
		</Container>
	);
}
