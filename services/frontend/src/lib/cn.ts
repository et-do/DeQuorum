/**
 * Tailwind-aware className composer.
 *
 *   cn("p-4", condition && "bg-bg-muted", className)
 *
 * `clsx` handles conditional values + arrays; `twMerge` resolves Tailwind
 * conflicts so later utilities win (e.g. `cn("p-4", "p-6")` → `"p-6"`).
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
	return twMerge(clsx(inputs));
}
