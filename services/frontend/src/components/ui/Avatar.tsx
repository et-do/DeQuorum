import { useMemo } from "react";
import { cn } from "@/lib/cn";

/**
 * Deterministic identicon from a string seed (typically `contributor_id`).
 *
 * Renders a 5×5 symmetric pixel grid (Github-style identicon) plus a
 * background color derived from the seed's hash. Same seed → same icon,
 * forever — useful for visually distinguishing contributors without
 * trusting any external avatar service.
 */
export function Avatar({
	seed,
	size = 32,
	className,
}: {
	seed: string;
	size?: number;
	className?: string;
}) {
	const { cells, fg } = useMemo(() => identicon(seed), [seed]);

	return (
		<svg
			width={size}
			height={size}
			viewBox="0 0 5 5"
			role="img"
			aria-label={`Avatar for ${seed}`}
			className={cn("shrink-0 border border-border", className)}
		>
			<rect width="5" height="5" fill="var(--bg-muted)" />
			{cells.map(([x, y], i) => (
				<rect key={i} x={x} y={y} width={1} height={1} fill={fg} shapeRendering="crispEdges" />
			))}
			{/* size legend so the grid actually shows */}
			<title>{seed.slice(0, 12)}</title>
		</svg>
	);
}

function identicon(seed: string): {
	cells: [number, number][];
	fg: string;
} {
	// FNV-1a 32-bit, plenty for an identicon.
	let h = 0x811c9dc5;
	for (let i = 0; i < seed.length; i++) {
		h ^= seed.charCodeAt(i);
		h = Math.imul(h, 0x01000193);
	}
	const cells: [number, number][] = [];
	// Only the left 3 columns; mirror to the right for symmetry.
	for (let y = 0; y < 5; y++) {
		for (let x = 0; x < 3; x++) {
			h = Math.imul(h ^ ((x + y * 3) | 0), 0x01000193);
			if ((h & 1) === 1) {
				cells.push([x, y]);
				if (x < 2) cells.push([4 - x, y]);
			}
		}
	}
	// Foreground: use a CSS variable so it adapts to theme.
	return { cells, fg: "var(--fg)" };
}
