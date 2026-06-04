import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Title + optional description + optional actions slot. Each route's
 * top section uses this for a consistent layout.
 */
export function PageHeader({
	eyebrow,
	title,
	description,
	actions,
	className,
}: {
	eyebrow?: ReactNode;
	title: ReactNode;
	description?: ReactNode;
	actions?: ReactNode;
	className?: string;
}) {
	return (
		<header
			className={cn(
				"flex flex-wrap items-end justify-between gap-4 border-b border-border pb-6",
				className,
			)}
		>
			<div className="space-y-1">
				{eyebrow && (
					<div className="text-xs uppercase tracking-widest text-fg-subtle">{eyebrow}</div>
				)}
				<h1 className="text-2xl font-bold tracking-tight">{title}</h1>
				{description && <p className="text-sm text-fg-muted">{description}</p>}
			</div>
			{actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
		</header>
	);
}
