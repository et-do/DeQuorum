import { createFileRoute } from "@tanstack/react-router";
import { Markdown } from "@/components/chat/Markdown";
import { Container } from "@/components/ui/Container";
import { WHITEPAPER_MARKDOWN } from "@/content/whitepaper";

export const Route = createFileRoute("/whitepaper")({
	component: WhitepaperPage,
	head: () => ({
		meta: [
			{
				title: "DeQuorum — Whitepaper",
			},
			{
				name: "description",
				content:
					"A crowdsourced, verifiable, contributor-owned foundational AI. The architecture, governance, and economics of DeQuorum.",
			},
		],
	}),
});

function WhitepaperPage() {
	return (
		<Container className="py-16 sm:py-24">
			<article className="mx-auto max-w-3xl">
				<Markdown text={WHITEPAPER_MARKDOWN} />
			</article>
		</Container>
	);
}
