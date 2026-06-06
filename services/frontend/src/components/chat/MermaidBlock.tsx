import mermaid from "mermaid";
import { useEffect, useId, useRef, useState } from "react";

/**
 * Renders a `mermaid` source string as inline SVG.
 *
 * - Initializes mermaid once per page, theme-aware via `data-theme`.
 * - Re-renders on theme flips so the diagram colors track the host UI.
 * - Falls back to a plain `<pre>` block with the source if mermaid
 *   throws on a malformed diagram (common during streaming, where the
 *   source arrives incrementally).
 */

let initialized = false;
function ensureInitialized(theme: "dark" | "default") {
	if (initialized) {
		mermaid.initialize({
			startOnLoad: false,
			theme,
			securityLevel: "strict",
			fontFamily: "inherit",
		});
		return;
	}
	mermaid.initialize({
		startOnLoad: false,
		theme,
		securityLevel: "strict",
		fontFamily: "inherit",
	});
	initialized = true;
}

function currentMermaidTheme(): "dark" | "default" {
	if (typeof document === "undefined") return "default";
	const dataTheme = document.documentElement.getAttribute("data-theme");
	return dataTheme === "dark" ? "dark" : "default";
}

export function MermaidBlock({ source }: { source: string }) {
	const rawId = useId();
	// Mermaid expects DOM-id-safe identifiers (no colons).
	const id = `mermaid-${rawId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
	const containerRef = useRef<HTMLDivElement>(null);
	const [svg, setSvg] = useState<string | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		let cancelled = false;
		const render = async () => {
			ensureInitialized(currentMermaidTheme());
			try {
				const { svg: out } = await mermaid.render(id, source);
				if (!cancelled) {
					setSvg(out);
					setError(null);
				}
			} catch (err) {
				if (!cancelled) setError(String(err));
			}
		};
		render();
		const observer = new MutationObserver(render);
		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ["data-theme"],
		});
		return () => {
			cancelled = true;
			observer.disconnect();
		};
	}, [id, source]);

	if (error) {
		return (
			<pre className="overflow-x-auto rounded-md bg-bg-muted p-3 text-xs text-fg-muted">
				<code>{source}</code>
			</pre>
		);
	}
	return (
		<div
			ref={containerRef}
			className="mermaid-diagram my-4 flex justify-center"
			// mermaid renders to an SVG string; injecting via
			// dangerouslySetInnerHTML is the official integration. Source
			// always comes from a ```mermaid fenced code block in our own
			// markdown, never from arbitrary user HTML. We also pass
			// `securityLevel: "strict"` to mermaid so it sanitizes any
			// labels at render time.
			// biome-ignore lint/security/noDangerouslySetInnerHtml: SVG output from mermaid
			dangerouslySetInnerHTML={svg ? { __html: svg } : undefined}
		/>
	);
}
