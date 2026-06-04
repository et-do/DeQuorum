import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
	it("renders its children", () => {
		render(<Button>Launch App</Button>);
		expect(screen.getByRole("button", { name: /launch app/i })).toBeInTheDocument();
	});

	it("fires onClick", async () => {
		const user = userEvent.setup();
		const onClick = vi.fn();
		render(<Button onClick={onClick}>Click me</Button>);
		await user.click(screen.getByRole("button"));
		expect(onClick).toHaveBeenCalledTimes(1);
	});

	it("does not fire onClick when disabled", async () => {
		const user = userEvent.setup();
		const onClick = vi.fn();
		render(
			<Button disabled onClick={onClick}>
				Inert
			</Button>,
		);
		await user.click(screen.getByRole("button"));
		expect(onClick).not.toHaveBeenCalled();
	});

	it("defaults to type=button (not submit) to avoid accidental form submission", () => {
		render(<Button>Click</Button>);
		expect(screen.getByRole("button")).toHaveAttribute("type", "button");
	});
});
