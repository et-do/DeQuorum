import type { ReactNode } from "react";
import { useEffect } from "react";
import { cn } from "@/lib/cn";

/**
 * Minimal modal dialog. Uses the native HTML `<dialog>` element for
 * focus trapping + Escape-to-close, dressed in our chrome.
 *
 * Controlled by `open`; closes via `onClose`. Backdrop click closes by
 * default (override with `dismissable={false}`).
 */
export function Dialog({
	open,
	onClose,
	title,
	children,
	className,
	dismissable = true,
}: {
	open: boolean;
	onClose: () => void;
	title?: ReactNode;
	children: ReactNode;
	className?: string;
	dismissable?: boolean;
}) {
	useEffect(() => {
		if (!open) return;
		const handler = (e: KeyboardEvent) => {
			if (dismissable && e.key === "Escape") onClose();
		};
		document.addEventListener("keydown", handler);
		return () => document.removeEventListener("keydown", handler);
	}, [open, dismissable, onClose]);

	if (!open) return null;

	return (
		<div
			className="fixed inset-0 z-50 flex items-center justify-center bg-bg/80 p-4 backdrop-blur-sm"
			onMouseDown={(e) => {
				if (dismissable && e.target === e.currentTarget) onClose();
			}}
		>
			<div
				role="dialog"
				aria-modal="true"
				className={cn("w-full max-w-lg border border-border-strong bg-bg p-6 shadow-lg", className)}
			>
				{title && <h2 className="mb-4 text-lg font-bold tracking-tight">{title}</h2>}
				{children}
			</div>
		</div>
	);
}
