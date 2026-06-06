import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "@/lib/theme";

// Mock TanStack Router's Link + useRouterState so TopNav can render
// without a router context. We're asserting on chrome (brand mark, nav
// labels, theme toggle, conditional CTA), not routing behavior.
const mockPathname = vi.fn(() => "/");
vi.mock("@tanstack/react-router", () => ({
	Link: ({ to, children, "aria-label": ariaLabel, ...rest }: any) => (
		<a href={to} aria-label={ariaLabel} {...rest}>
			{children}
		</a>
	),
	useRouterState: ({ select }: { select: (s: any) => unknown }) =>
		select({ location: { pathname: mockPathname() } }),
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
		mockPathname.mockReturnValue("/");
		renderTopNav();
		expect(screen.getByLabelText(/dequorum home/i)).toHaveAttribute("href", "/");
	});

	it.each(["About", "Whitepaper", "Docs", "Pricing"])("renders nav link: %s", (label) => {
		mockPathname.mockReturnValue("/");
		renderTopNav();
		expect(screen.getByRole("link", { name: new RegExp(`^${label}$`, "i") })).toBeInTheDocument();
	});

	it("renders the theme toggle", () => {
		mockPathname.mockReturnValue("/");
		renderTopNav();
		expect(
			screen.getByRole("button", { name: /switch to (light|dark) mode/i }),
		).toBeInTheDocument();
	});

	it("hides the Launch App CTA on the landing page", () => {
		mockPathname.mockReturnValue("/");
		renderTopNav();
		expect(screen.queryByRole("link", { name: /launch app/i })).not.toBeInTheDocument();
	});

	it("shows the Launch App CTA on sub-pages", () => {
		mockPathname.mockReturnValue("/about");
		renderTopNav();
		expect(screen.getByRole("link", { name: /launch app/i })).toBeInTheDocument();
	});
});
