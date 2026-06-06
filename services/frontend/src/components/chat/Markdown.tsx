import "katex/dist/katex.min.css";

import { Children, isValidElement, memo, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import { CodeBlock } from "./CodeBlock";
import { MermaidBlock } from "./MermaidBlock";

/**
 * Recover the original code source from rehype-highlight's transformed
 * children tree. Highlighting wraps tokens in nested `<span>`s; the
 * eventual leaves are still plain text nodes, so a depth-first
 * concatenation reconstructs the original string verbatim.
 */
function reactChildrenToText(node: ReactNode): string {
	if (node == null || typeof node === "boolean") return "";
	if (typeof node === "string" || typeof node === "number") return String(node);
	if (Array.isArray(node)) return node.map(reactChildrenToText).join("");
	if (isValidElement<{ children?: ReactNode }>(node)) {
		return reactChildrenToText(node.props.children);
	}
	return "";
}

/**
 * Streaming-friendly markdown renderer.
 *
 * - GFM (tables, strikethrough, task lists) via remark-gfm.
 * - LaTeX math: $inline$ + $$display$$ via remark-math + rehype-katex.
 * - Code blocks: syntax highlighting via rehype-highlight; color
 *   theme lives in src/styles/index.css under the .markdown scope.
 * - Mermaid diagrams: any ```mermaid fence renders as an SVG via
 *   `MermaidBlock`. Same source string works in GitHub-rendered
 *   markdown AND the in-app whitepaper route.
 *
 * Accepts partial input (incomplete fences, half-written tables) —
 * react-markdown tolerates this and renders what it can each frame,
 * which matters for the streaming-chat code path.
 */
export const Markdown = memo(function Markdown({ text }: { text: string }) {
	return (
		<div className="markdown text-sm leading-relaxed text-fg">
			<ReactMarkdown
				remarkPlugins={[remarkGfm, remarkMath]}
				rehypePlugins={[
					[rehypeHighlight, { detect: true, ignoreMissing: true }],
					[rehypeKatex, { strict: false, throwOnError: false }],
				]}
				components={{
					a: ({ node: _n, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
					code: ({ node: _n, className, children, ...props }) => {
						// Intercept ```mermaid fences and hand the source
						// to MermaidBlock. Other languages fall through to
						// the rehype-highlight default rendering; the copy
						// affordance is added by the `pre` override below
						// so inline code stays unwrapped.
						const match = /language-mermaid/.exec(className ?? "");
						if (match) {
							return <MermaidBlock source={String(children).trim()} />;
						}
						return (
							<code className={className} {...props}>
								{children}
							</code>
						);
					},
					pre: ({ node: _n, children, ...props }) => {
						// Wrap fenced code blocks with the copy-enabled
						// CodeBlock. A `pre` whose only child isn't a
						// `<code>` (rare; e.g. raw HTML pre) falls through
						// unchanged.
						const first = Children.toArray(children)[0];
						if (
							isValidElement<{ className?: string; children?: ReactNode }>(first) &&
							first.type === "code"
						) {
							const source = reactChildrenToText(first.props.children);
							return (
								<CodeBlock className={first.props.className} source={source}>
									{children}
								</CodeBlock>
							);
						}
						return <pre {...props}>{children}</pre>;
					},
				}}
			>
				{text}
			</ReactMarkdown>
		</div>
	);
});
