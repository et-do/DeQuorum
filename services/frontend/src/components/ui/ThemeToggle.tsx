import { useTheme } from "@/lib/theme";

/**
 * Simple sun/moon glyph toggle. Renders a single character that flips
 * between light and dark; aria-label updates so screen readers announce
 * the action that will be taken on click.
 */
export function ThemeToggle() {
	const { theme, toggle } = useTheme();
	const next = theme === "light" ? "dark" : "light";
	return (
		<button
			type="button"
			onClick={toggle}
			aria-label={`Switch to ${next} mode`}
			title={`Switch to ${next} mode`}
			className="inline-flex h-8 w-8 items-center justify-center border border-border-strong text-fg transition-colors hover:bg-bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fg"
		>
			<span aria-hidden="true" className="text-base leading-none">
				{theme === "light" ? "○" : "●"}
			</span>
		</button>
	);
}
