import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Placeholder shown when a list or section has no data. Always pairs
 * a primary message with an optional CTA so dead ends are rare.
 */
export function EmptyState({
	title,
	description,
	action,
	className,
}: {
	title: ReactNode;
	description?: ReactNode;
	action?: ReactNode;
	className?: string;
}) {
	return (
		<div
			className={cn(
				"flex flex-col items-center justify-center gap-3 border border-dashed border-border bg-bg-muted px-6 py-12 text-center",
				className,
			)}
		>
			<div className="font-bold tracking-tight">{title}</div>
			{description && <p className="max-w-md text-sm text-fg-muted">{description}</p>}
			{action && <div className="mt-2">{action}</div>}
		</div>
	);
}
