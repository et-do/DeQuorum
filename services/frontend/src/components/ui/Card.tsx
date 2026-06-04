import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Generic panel chrome. The whole UI uses 1px borders + flat fills (no
 * shadows, no radii) so cards are visually consistent without any extra
 * design system.
 */
export function Card({
	children,
	className,
	as: As = "div",
}: {
	children: ReactNode;
	className?: string;
	as?: "div" | "section" | "article" | "aside";
}) {
	return <As className={cn("border border-border bg-bg p-5", className)}>{children}</As>;
}

export function CardHeader({
	title,
	subtitle,
	actions,
	className,
}: {
	title: ReactNode;
	subtitle?: ReactNode;
	actions?: ReactNode;
	className?: string;
}) {
	return (
		<header className={cn("mb-4 flex flex-wrap items-start justify-between gap-3", className)}>
			<div className="space-y-1">
				<div className="font-bold tracking-tight">{title}</div>
				{subtitle && (
					<div className="text-xs uppercase tracking-widest text-fg-subtle">{subtitle}</div>
				)}
			</div>
			{actions && <div className="flex items-center gap-2">{actions}</div>}
		</header>
	);
}
