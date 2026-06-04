import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ThemeProvider } from "@/lib/theme";
import { ThemeToggle } from "./ThemeToggle";

function renderToggle() {
	return render(
		<ThemeProvider>
			<ThemeToggle />
		</ThemeProvider>,
	);
}

describe("ThemeToggle", () => {
	it("flips the document data-theme on click", async () => {
		const user = userEvent.setup();
		renderToggle();

		// Initial theme is "light" (matchMedia is mocked to return matches:false).
		expect(document.documentElement.getAttribute("data-theme")).toBe("light");

		await user.click(screen.getByRole("button", { name: /switch to dark/i }));
		expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

		await user.click(screen.getByRole("button", { name: /switch to light/i }));
		expect(document.documentElement.getAttribute("data-theme")).toBe("light");
	});

	it("persists the chosen theme to localStorage", async () => {
		const user = userEvent.setup();
		renderToggle();

		await user.click(screen.getByRole("button", { name: /switch to dark/i }));
		expect(window.localStorage.getItem("dequorum.theme")).toBe("dark");
	});

	it("updates its aria-label to announce the action that will be taken", async () => {
		const user = userEvent.setup();
		renderToggle();

		expect(screen.getByRole("button", { name: /switch to dark mode/i })).toBeInTheDocument();

		await user.click(screen.getByRole("button"));
		expect(screen.getByRole("button", { name: /switch to light mode/i })).toBeInTheDocument();
	});
});
