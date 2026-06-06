import { useState } from "react";
import { useToasts } from "@/lib/toasts";

/**
 * Renders a `<pre><code>` fence with a hover-revealed copy button.
 *
 * react-markdown delivers the language label via the child `<code>`'s
 * className (`language-python`, `language-bash`, etc). We surface
 * that label in the header so a reader sees what they're copying.
 *
 * Copy uses the Clipboard API with a graceful execCommand fallback
 * for older WebViews; either way the user gets the same toast.
 */
export function CodeBlock({
	className,
	source,
	children,
}: {
	className?: string;
	source: string;
	children: React.ReactNode;
}) {
	const { toast } = useToasts();
	const [copied, setCopied] = useState(false);
	const language = /language-([\w-]+)/.exec(className ?? "")?.[1] ?? "";

	const onCopy = async () => {
		try {
			if (navigator.clipboard?.writeText) {
				await navigator.clipboard.writeText(source);
			} else {
				const ta = document.createElement("textarea");
				ta.value = source;
				ta.style.position = "fixed";
				ta.style.opacity = "0";
				document.body.appendChild(ta);
				ta.select();
				document.execCommand("copy");
				document.body.removeChild(ta);
			}
			setCopied(true);
			toast("Copied to clipboard", { tone: "success" });
			window.setTimeout(() => setCopied(false), 1500);
		} catch {
			toast("Copy failed", { tone: "error" });
		}
	};

	return (
		<div className="codeblock group relative my-3 rounded-md bg-bg-muted">
			<div className="flex items-center justify-between border-b border-border/40 px-3 py-1.5 text-[10px] uppercase tracking-widest text-fg-subtle">
				<span>{language || "text"}</span>
				<button
					type="button"
					onClick={onCopy}
					aria-label={copied ? "Copied" : "Copy code"}
					className="rounded px-2 py-0.5 text-fg-subtle opacity-0 transition-opacity hover:bg-bg hover:text-fg group-hover:opacity-100 focus:opacity-100"
				>
					{copied ? "✓ Copied" : "Copy"}
				</button>
			</div>
			<pre className="overflow-x-auto px-3 py-2 text-[0.82rem] leading-relaxed">{children}</pre>
		</div>
	);
}
