/**
 * Global Vitest setup.
 *
 *   - Extends `expect` with @testing-library/jest-dom matchers
 *     (`toBeInTheDocument`, `toHaveTextContent`, etc.).
 *   - Mocks `matchMedia` since jsdom doesn't implement it and our theme
 *     provider reads `prefers-color-scheme` at startup.
 *   - Installs an in-memory `localStorage`. jsdom only exposes
 *     `window.localStorage` when its document has a non-opaque origin, which
 *     doesn't hold reliably across CI/container environments under vitest 4 +
 *     jsdom 25 — without this the afterEach `localStorage.clear()` throws
 *     "Cannot read properties of undefined". An explicit mock also keeps
 *     storage deterministic between tests.
 */

import "@testing-library/jest-dom/vitest";
import { afterEach, beforeAll, vi } from "vitest";

function createMemoryStorage(): Storage {
	const store = new Map<string, string>();
	return {
		get length() {
			return store.size;
		},
		clear: () => store.clear(),
		getItem: (key) => (store.has(key) ? (store.get(key) as string) : null),
		key: (index) => Array.from(store.keys())[index] ?? null,
		removeItem: (key) => void store.delete(key),
		setItem: (key, value) => void store.set(key, String(value)),
	};
}

beforeAll(() => {
	Object.defineProperty(window, "localStorage", {
		writable: true,
		configurable: true,
		value: createMemoryStorage(),
	});
	Object.defineProperty(window, "matchMedia", {
		writable: true,
		value: vi.fn().mockImplementation((query: string) => ({
			matches: false,
			media: query,
			onchange: null,
			addListener: vi.fn(),
			removeListener: vi.fn(),
			addEventListener: vi.fn(),
			removeEventListener: vi.fn(),
			dispatchEvent: vi.fn(),
		})),
	});
});

afterEach(() => {
	window.localStorage.clear();
	document.documentElement.removeAttribute("data-theme");
});
