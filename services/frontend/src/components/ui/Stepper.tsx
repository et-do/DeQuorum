import { cn } from "@/lib/cn";

/**
 * Horizontal step indicator. Reads `current` (zero-indexed) and renders
 * one tick per step with the current/past distinguished.
 */
export function Stepper({
	steps,
	current,
	className,
}: {
	steps: { label: string }[];
	current: number;
	className?: string;
}) {
	return (
		<ol
			aria-label="Progress"
			className={cn("flex items-center gap-2 text-xs uppercase tracking-widest", className)}
		>
			{steps.map((s, i) => {
				const done = i < current;
				const active = i === current;
				return (
					<li
						key={s.label}
						aria-current={active ? "step" : undefined}
						className={cn(
							"flex items-center gap-2",
							i > 0 && "before:inline-block before:h-px before:w-6 before:bg-border",
						)}
					>
						<span
							className={cn(
								"inline-flex h-6 w-6 items-center justify-center border",
								done || active ? "border-fg bg-fg text-bg" : "border-border bg-bg text-fg-subtle",
							)}
						>
							{i + 1}
						</span>
						<span
							className={cn(
								"hidden sm:inline",
								active ? "text-fg" : done ? "text-fg-muted" : "text-fg-subtle",
							)}
						>
							{s.label}
						</span>
					</li>
				);
			})}
		</ol>
	);
}
