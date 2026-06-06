import { cn } from "@/lib/cn";

/**
 * Loading placeholder. The pulse animation is intentionally subtle —
 * monochrome opacity flicker rather than a shimmer gradient, to match
 * the rest of the UI.
 */
export function Skeleton({
	className,
	as: As = "div",
}: {
	className?: string;
	as?: "div" | "span";
}) {
	return (
		<As
			aria-hidden="true"
			className={cn("shimmer block rounded-md border border-border bg-bg-muted", className)}
		/>
	);
}
