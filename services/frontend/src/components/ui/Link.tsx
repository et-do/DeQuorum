import { type LinkProps, Link as RouterLink } from "@tanstack/react-router";
import type { AnchorHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const LINK_STYLES =
	"underline-offset-4 hover:underline focus-visible:outline-none focus-visible:underline";

/**
 * Internal navigation — preserves SPA semantics through TanStack Router.
 * Use for any path that the React app owns.
 */
export function NavLink({ className, ...props }: LinkProps) {
	return (
		<RouterLink
			{...props}
			className={cn(LINK_STYLES, "text-fg", className as string | undefined)}
		/>
	);
}

/**
 * External (or cross-origin) anchor — always opens in the current tab by
 * default; pass target="_blank" explicitly when warranted. Carries the same
 * underline-on-hover treatment as NavLink for visual consistency.
 */
export function ExternalLink({
	className,
	target,
	rel,
	...props
}: AnchorHTMLAttributes<HTMLAnchorElement>) {
	return (
		<a
			{...props}
			target={target}
			rel={target === "_blank" ? (rel ?? "noopener noreferrer") : rel}
			className={cn(LINK_STYLES, "text-fg", className)}
		/>
	);
}
