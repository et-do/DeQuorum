import { useCallback, useEffect, useState } from "react";

/**
 * useState backed by localStorage. Reads once on mount (after first
 * render so SSR / hydration stays clean), writes on every change.
 */
export function useLocalStorageState<T>(
	key: string,
	initialValue: T,
): [T, (next: T | ((prev: T) => T)) => void] {
	const [value, setValue] = useState<T>(initialValue);

	// We intentionally only read once on mount; the key is treated as
	// fixed across the lifetime of the component (changing the key
	// mid-mount would mean a different state binding entirely).
	// biome-ignore lint/correctness/useExhaustiveDependencies: read-once on mount
	useEffect(() => {
		try {
			const raw = window.localStorage.getItem(key);
			if (raw !== null) setValue(JSON.parse(raw) as T);
		} catch {
			// ignore malformed JSON
		}
	}, []);

	const update = useCallback(
		(next: T | ((prev: T) => T)) => {
			setValue((prev) => {
				const resolved = typeof next === "function" ? (next as (p: T) => T)(prev) : next;
				try {
					window.localStorage.setItem(key, JSON.stringify(resolved));
				} catch {
					// quota or private-mode — swallow
				}
				return resolved;
			});
		},
		[key],
	);

	return [value, update];
}
