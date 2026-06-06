import { useMutation, useQuery } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { listCategories, submitContribution } from "@/lib/api";
import { useToasts } from "@/lib/toasts";

export const Route = createFileRoute("/app/contribute/new")({
	component: NewSubmission,
});

function NewSubmission() {
	const navigate = useNavigate();
	const { toast } = useToasts();
	const categories = useQuery({ queryKey: ["categories"], queryFn: listCategories });
	const [categoryId, setCategoryId] = useState("");
	const [text, setText] = useState("");
	const [citations, setCitations] = useState("");
	const [sourceUrl, setSourceUrl] = useState("");

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
		if (!categoryId || !text.trim()) return;
		// Stopgap: a `Source URL` field is folded into the citation list as
		// the leading entry, so v0.1 contributions filed from a larger
		// document still carry a back-reference. When the bulk-ingestion
		// flow lands (v0.2 — see docs/architecture/contribution-sources.md)
		// these get migrated into proper `documents` rows.
		const cites = citations
			.split(/\r?\n/)
			.map((c) => c.trim())
			.filter(Boolean);
		const allCitations = sourceUrl.trim() ? [sourceUrl.trim(), ...cites] : cites;
		mutation.mutate({
			primary_category_id: categoryId,
			text: text.trim(),
			citations: allCitations,
		});
	}

	// Only leaf categories with a curated persona accept new contributions
	// — those are the ones the router can target. Organizational parent
	// nodes are excluded from the picker.
	const routableCategories = categories.data?.filter((c) => c.is_routable) ?? [];

	return (
		<div className="mx-auto max-w-3xl space-y-8">
			<PageHeader
				title="New submission"
				description="File a signed claim under a curated category. Reviewers will vote."
			/>

			<div className="rounded-md border border-border bg-bg-muted/50 p-3 text-xs text-fg-muted">
				<strong className="font-bold text-fg">Bulk submission</strong> — ingesting a documentation
				site, paper, or repo and extracting multiple claims at once is on the v0.2 milestone. Today
				you can submit one claim at a time; add the source URL below so it back-links to wherever
				the claim came from.
			</div>

			<form onSubmit={onSubmit}>
				<Card className="space-y-5">
					<div>
						<label className="block text-xs uppercase tracking-widest text-fg-subtle">
							Category
						</label>
						<select
							value={categoryId}
							onChange={(e) => setCategoryId(e.target.value)}
							required
							className="mt-1 w-full border border-border bg-bg px-3 py-2 text-fg focus:border-border-strong focus:outline-none"
						>
							<option value="">— select —</option>
							{routableCategories.map((c) => (
								<option key={c.category_id} value={c.category_id}>
									{c.display_name}
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
							Source URL (optional)
						</label>
						<input
							type="url"
							value={sourceUrl}
							onChange={(e) => setSourceUrl(e.target.value)}
							placeholder="https:// — where this claim came from"
							className="mt-1 w-full border border-border bg-bg px-3 py-2 text-fg placeholder:text-fg-subtle focus:border-border-strong focus:outline-none"
						/>
						<p className="mt-1 text-[11px] text-fg-subtle">
							Doc page, paper, repo file, blog post — whatever this claim is sourced from.
						</p>
					</div>

					<div>
						<label className="block text-xs uppercase tracking-widest text-fg-subtle">
							Additional citations (one per line, https only)
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
