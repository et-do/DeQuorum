import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "ghost";
type Size = "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
	variant?: Variant;
	size?: Size;
}

/**
 * Monochrome, uppercased monospace button matching the Bittensor reference.
 * `primary` inverts colors (bg=fg, fg=bg) so it reads as a hard-edged CTA;
 * `ghost` is a transparent button with a 1px border that fills on hover.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
	{ variant = "primary", size = "md", className, type, ...props },
	ref,
) {
	return (
		<button
			ref={ref}
			type={type ?? "button"}
			className={cn(
				"inline-flex items-center justify-center gap-2 rounded-md border font-mono uppercase tracking-wider transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fg focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:pointer-events-none disabled:opacity-50",
				size === "md" && "px-4 py-2 text-sm",
				size === "lg" && "px-6 py-3 text-base",
				variant === "primary" && "border-accent bg-accent text-accent-fg hover:opacity-90",
				variant === "ghost" && "border-border-strong bg-transparent text-fg hover:bg-bg-muted",
				className,
			)}
			{...props}
		/>
	);
});
