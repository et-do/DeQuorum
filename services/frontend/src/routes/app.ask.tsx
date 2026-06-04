import { useMutation } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { runQuery } from "@/lib/api";
import { useToasts } from "@/lib/toasts";

export const Route = createFileRoute("/app/ask")({
	component: AskRoute,
});

function AskRoute() {
	const { toast } = useToasts();
	const [text, setText] = useState("");
	const mutation = useMutation({
		mutationFn: runQuery,
		onSuccess: () => toast("Answer ready", { tone: "success" }),
		onError: (e: Error) => toast(e.message, { tone: "error", durationMs: 8000 }),
	});

	function onSubmit(e: FormEvent<HTMLFormElement>) {
		e.preventDefault();
		if (text.trim()) mutation.mutate(text.trim());
	}

	const response = mutation.data;

	return (
		<div className="mx-auto max-w-3xl space-y-8">
			<PageHeader title="Ask" description="Query the panel." />

			<form onSubmit={onSubmit} className="space-y-3">
				<label className="block text-xs uppercase tracking-widest text-fg-subtle">Question</label>
				<textarea
					value={text}
					onChange={(e) => setText(e.target.value)}
					rows={4}
					placeholder="python typing generator"
					className="w-full border border-border bg-bg px-3 py-2 text-fg placeholder:text-fg-subtle focus:border-border-strong focus:outline-none"
				/>
				<div className="flex items-center gap-3">
					<Button type="submit" disabled={mutation.isPending}>
						{mutation.isPending ? "Running…" : "Run"}
					</Button>
				</div>
			</form>

			{response && (
				<section className="space-y-4">
					<Card>
						<div className="text-xs uppercase tracking-widest text-fg-subtle">Answer</div>
						<pre className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">
							{response.final_answer}
						</pre>
					</Card>

					<Card>
						<div className="text-xs uppercase tracking-widest text-fg-subtle">
							Routing · {response.routing.method}
							{response.routing.fallback_used ? " · fallback" : ""}
						</div>
						<ul className="mt-3 space-y-1 text-sm text-fg-muted">
							{response.routing.selected.map((s) => (
								<li key={s.expert_id}>
									<span className="text-fg">{s.expert_id}</span> · {s.score.toFixed(3)}
								</li>
							))}
						</ul>
					</Card>

					<Card>
						<div className="text-xs uppercase tracking-widest text-fg-subtle">Ledger credits</div>
						<ul className="mt-3 space-y-1 text-sm text-fg-muted">
							{Object.entries(response.ledger).map(([k, v]) => (
								<li key={k}>
									<span className="text-fg">{k}</span>: {v}
								</li>
							))}
						</ul>
					</Card>
				</section>
			)}
		</div>
	);
}
