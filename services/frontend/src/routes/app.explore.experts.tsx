import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { listExperts } from "@/lib/api";

export const Route = createFileRoute("/app/explore/experts")({
	component: ExpertsRoute,
});

function ExpertsRoute() {
	const q = useQuery({ queryKey: ["experts"], queryFn: listExperts });

	return (
		<div className="space-y-8">
			<PageHeader
				title="Experts"
				description="Seed personas; each one specializes in a slice of the network's domain."
			/>

			{q.isLoading ? (
				<div className="grid gap-4 md:grid-cols-2">
					<Skeleton className="h-40" />
					<Skeleton className="h-40" />
				</div>
			) : (
				<ul className="grid gap-4 md:grid-cols-2">
					{q.data?.map((e) => (
						<li key={e.expert_id}>
							<Card>
								<CardHeader title={e.expert_id} subtitle={e.specialty_tags.join(" · ")} />
								<p className="text-sm text-fg-muted">{e.prompt_digest}</p>
								{e.example_questions.length > 0 && (
									<details className="mt-3 text-sm">
										<summary className="cursor-pointer text-xs uppercase tracking-widest text-fg-subtle">
											Example questions
										</summary>
										<ul className="mt-2 space-y-1 text-fg-muted">
											{e.example_questions.map((qn) => (
												<li key={qn}>· {qn}</li>
											))}
										</ul>
									</details>
								)}
							</Card>
						</li>
					))}
				</ul>
			)}
		</div>
	);
}
