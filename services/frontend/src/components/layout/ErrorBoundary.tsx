import { Component, type ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

/**
 * Class-component error boundary. Catches render-time exceptions and
 * shows a card with a Retry button (which clears local state and lets
 * React try again).
 *
 * For data-fetching errors, prefer query-level error handling — this is
 * the last-resort fallback.
 */
interface State {
	error: Error | null;
}

export class ErrorBoundary extends Component<
	{ children: ReactNode; fallback?: (error: Error, reset: () => void) => ReactNode },
	State
> {
	state: State = { error: null };

	static getDerivedStateFromError(error: Error): State {
		return { error };
	}

	componentDidCatch(error: Error) {
		// Hook for future telemetry sink. Console for now.
		console.error("[ErrorBoundary] caught", error);
	}

	reset = () => this.setState({ error: null });

	render() {
		if (this.state.error) {
			if (this.props.fallback) {
				return this.props.fallback(this.state.error, this.reset);
			}
			return (
				<Card className="mx-auto my-12 max-w-lg text-center">
					<div className="text-xs uppercase tracking-widest text-fg-subtle">Error</div>
					<div className="mt-2 font-bold tracking-tight">Something broke</div>
					<p className="mt-2 text-sm text-fg-muted">{this.state.error.message}</p>
					<div className="mt-6">
						<Button onClick={this.reset}>Try again</Button>
					</div>
				</Card>
			);
		}
		return this.props.children;
	}
}
