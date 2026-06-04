import { createFileRoute } from "@tanstack/react-router";
import { Container } from "@/components/ui/Container";

export const Route = createFileRoute("/docs")({
	component: DocsPage,
});

function DocsPage() {
	return (
		<Container className="space-y-10 py-16 sm:py-24">
			<header className="space-y-2">
				<h1 className="text-3xl font-bold tracking-tight sm:text-4xl">How it works</h1>
				<p className="text-fg-muted">One query, end to end.</p>
			</header>

			<Step
				n="01"
				title="Submit"
				body="A contributor publishes a claim tied to an expert persona. The submission is signed by their keypair."
			/>
			<Step
				n="02"
				title="Review"
				body="Peers vote. Two +1s approves; two -1s rejects. Approved claims enter the expert's knowledge base."
			/>
			<Step
				n="03"
				title="Route"
				body="A user's question is embedded and matched against the experts most likely to answer it."
			/>
			<Step
				n="04"
				title="Answer"
				body="Each routed expert pulls its top-cited approved claims and answers. The response is signed; citations link back to source."
			/>
			<Step
				n="05"
				title="Settle"
				body="Each query splits its fee between the node hoster who ran it, the contributors whose claims were cited, and the reviewers who curated quality."
			/>
		</Container>
	);
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
	return (
		<section className="grid grid-cols-[auto_1fr] gap-x-6">
			<span className="font-bold tracking-widest text-fg-subtle">{n}</span>
			<div className="space-y-1">
				<h2 className="font-bold tracking-tight">{title}</h2>
				<p className="text-fg-muted">{body}</p>
			</div>
		</section>
	);
}
