/**
 * Global Vitest setup.
 *
 *   - Extends `expect` with @testing-library/jest-dom matchers
 *     (`toBeInTheDocument`, `toHaveTextContent`, etc.).
 *   - Mocks `matchMedia` since jsdom doesn't implement it and our theme
 *     provider reads `prefers-color-scheme` at startup.
 *   - Resets localStorage between tests so theme persistence in one test
 *     doesn't leak into the next.
 */

import "@testing-library/jest-dom/vitest";
import { afterEach, beforeAll, vi } from "vitest";

beforeAll(() => {
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
