import { useMutation, useQuery } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { listExperts, submitContribution } from "@/lib/api";
import { useToasts } from "@/lib/toasts";

export const Route = createFileRoute("/app/contribute/new")({
	component: NewSubmission,
});

function NewSubmission() {
	const navigate = useNavigate();
	const { toast } = useToasts();
	const experts = useQuery({ queryKey: ["experts"], queryFn: listExperts });
	const [expertId, setExpertId] = useState("");
	const [text, setText] = useState("");
	const [citations, setCitations] = useState("");

	const mutation = useMutation({
		mutationFn: submitContribution,
		onSuccess: (c) => {
			toast("Submitted for review", { tone: "success" });
			navigate({
				to: "/app/explore/contributions/$id",
				params: { id: c.contribution_id },
			});
		},
		onError: (e: Error) => toast(e.message, { tone: "error", durationMs: 8000 }),
	});

	function onSubmit(e: FormEvent<HTMLFormElement>) {
		e.preventDefault();
		if (!expertId || !text.trim()) return;
		mutation.mutate({
			expert_id: expertId,
			text: text.trim(),
			citations: citations
				.split(/\r?\n/)
				.map((c) => c.trim())
				.filter(Boolean),
		});
	}

	return (
		<div className="mx-auto max-w-3xl space-y-8">
			<PageHeader
				title="New submission"
				description="Tie a signed claim to one of the seed experts. Reviewers will vote."
			/>

			<form onSubmit={onSubmit}>
				<Card className="space-y-5">
					<div>
						<label className="block text-xs uppercase tracking-widest text-fg-subtle">Expert</label>
						<select
							value={expertId}
							onChange={(e) => setExpertId(e.target.value)}
							required
							className="mt-1 w-full border border-border bg-bg px-3 py-2 text-fg focus:border-border-strong focus:outline-none"
						>
							<option value="">— select —</option>
							{experts.data?.map((e) => (
								<option key={e.expert_id} value={e.expert_id}>
									{e.expert_id} — {e.display_name}
								</option>
							))}
						</select>
					</div>

					<div>
						<label className="block text-xs uppercase tracking-widest text-fg-subtle">Claim</label>
						<textarea
							value={text}
							onChange={(e) => setText(e.target.value)}
							required
							minLength={50}
							rows={6}
							placeholder="At least 50 characters. State the claim plainly."
							className="mt-1 w-full border border-border bg-bg px-3 py-2 text-fg placeholder:text-fg-subtle focus:border-border-strong focus:outline-none"
						/>
					</div>

					<div>
						<label className="block text-xs uppercase tracking-widest text-fg-subtle">
							Citations (one per line, https only)
						</label>
						<textarea
							value={citations}
							onChange={(e) => setCitations(e.target.value)}
							rows={3}
							className="mt-1 w-full border border-border bg-bg px-3 py-2 text-fg placeholder:text-fg-subtle focus:border-border-strong focus:outline-none"
						/>
					</div>

					<div className="flex justify-end">
						<Button type="submit" disabled={mutation.isPending}>
							{mutation.isPending ? "Submitting…" : "Submit for review"}
						</Button>
					</div>
				</Card>
			</form>
		</div>
	);
}
