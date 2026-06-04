import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Centered max-width wrapper used by every route's content area. Keeps
 * the marketing copy comfortably narrow on wide screens while letting hero
 * sections breathe via `wide`.
 */
export function Container({
	children,
	wide = false,
	className,
}: {
	children: ReactNode;
	wide?: boolean;
	className?: string;
}) {
	return (
		<div className={cn("mx-auto w-full px-6", wide ? "max-w-6xl" : "max-w-3xl", className)}>
			{children}
		</div>
	);
}
