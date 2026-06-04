import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "default" | "muted" | "success" | "warning" | "danger" | "info";

/**
 * Status/role/tier chip. Monochrome by default; semantic tones use
 * minimal color to stay consistent with the rest of the UI.
 */
export function Badge({
	children,
	tone = "default",
	className,
}: {
	children: ReactNode;
	tone?: Tone;
	className?: string;
}) {
	return (
		<span
			className={cn(
				"inline-flex items-center gap-1 border px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest leading-tight",
				tone === "default" && "border-border-strong bg-bg-muted text-fg",
				tone === "muted" && "border-border bg-transparent text-fg-muted",
				tone === "success" && "border-border-strong bg-bg text-fg",
				tone === "warning" && "border-border-strong bg-bg-muted text-fg",
				tone === "danger" && "border-fg bg-fg text-bg",
				tone === "info" && "border-border-strong bg-transparent text-fg-muted",
				className,
			)}
		>
			{children}
		</span>
	);
}
