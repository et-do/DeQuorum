import { Container } from "@/components/ui/Container";
import { ExternalLink } from "@/components/ui/Link";

/**
 * Minimal footer. Single-line layout on desktop; stacks on mobile. The
 * GitHub link is the only external — everything else is page chrome.
 */
export function Footer() {
	return (
		<footer className="mt-auto border-t border-border bg-bg">
			<Container
				wide
				className="flex flex-col items-start justify-between gap-2 py-6 text-xs uppercase tracking-widest text-fg-subtle sm:flex-row sm:items-center"
			>
				<span>DeQuorum · Apache-2.0</span>
				<ExternalLink
					href="https://github.com/et-do/dequorum"
					target="_blank"
					className="text-fg-subtle hover:text-fg"
				>
					GitHub ↗
				</ExternalLink>
			</Container>
		</footer>
	);
}
