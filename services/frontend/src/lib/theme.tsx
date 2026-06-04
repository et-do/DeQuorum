/**
 * Theme provider and `useTheme` hook.
 *
 * Reads initial theme from (in priority order):
 *   1. localStorage (user's previously chosen preference)
 *   2. document's existing `data-theme` attribute (set by the inline
 *      no-flash script in index.html)
 *   3. `prefers-color-scheme` media query
 *   4. fallback: "light"
 *
 * Writes always go to both `<html data-theme>` and localStorage so a hard
 * reload picks up the same theme without flash.
 */

import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "dequorum.theme";

interface ThemeContextValue {
	theme: Theme;
	toggle: () => void;
	setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readInitialTheme(): Theme {
	if (typeof window === "undefined") return "light";
	const stored = window.localStorage.getItem(STORAGE_KEY);
	if (stored === "light" || stored === "dark") return stored;
	const fromAttr = document.documentElement.getAttribute("data-theme");
	if (fromAttr === "light" || fromAttr === "dark") return fromAttr;
	if (window.matchMedia?.("(prefers-color-scheme: dark)").matches) return "dark";
	return "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
	const [theme, setThemeState] = useState<Theme>(readInitialTheme);

	useEffect(() => {
		document.documentElement.setAttribute("data-theme", theme);
		window.localStorage.setItem(STORAGE_KEY, theme);
	}, [theme]);

	const setTheme = useCallback((next: Theme) => {
		setThemeState(next);
	}, []);

	const toggle = useCallback(() => {
		setThemeState((t) => (t === "light" ? "dark" : "light"));
	}, []);

	return (
		<ThemeContext.Provider value={{ theme, toggle, setTheme }}>{children}</ThemeContext.Provider>
	);
}

export function useTheme(): ThemeContextValue {
	const ctx = useContext(ThemeContext);
	if (!ctx) {
		throw new Error("useTheme must be used inside <ThemeProvider>");
	}
	return ctx;
}
