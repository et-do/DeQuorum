import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "@/lib/theme";

// Mock TanStack Router's Link to render a plain <a> in tests. We're
// asserting on TopNav's chrome (brand mark, nav labels, theme toggle),
// not on routing behavior — wiring up a full memory router for this
// unit test would be all setup, no signal.
vi.mock("@tanstack/react-router", () => ({
	Link: ({ to, children, "aria-label": ariaLabel, ...rest }: any) => (
		<a href={to} aria-label={ariaLabel} {...rest}>
			{children}
		</a>
	),
}));

// Import AFTER vi.mock so the mocked module is what TopNav resolves.
const { TopNav } = await import("./TopNav");

function renderTopNav() {
	return render(
		<ThemeProvider>
			<TopNav />
		</ThemeProvider>,
	);
}

describe("TopNav", () => {
	it("renders the brand mark linking home", () => {
		renderTopNav();
		expect(screen.getByLabelText(/dequorum home/i)).toHaveAttribute("href", "/");
	});

	it.each(["About", "Docs", "Pricing"])("renders nav link: %s", (label) => {
		renderTopNav();
		expect(screen.getByRole("link", { name: new RegExp(`^${label}$`, "i") })).toBeInTheDocument();
	});

	it("renders the theme toggle", () => {
		renderTopNav();
		expect(
			screen.getByRole("button", { name: /switch to (light|dark) mode/i }),
		).toBeInTheDocument();
	});
});
