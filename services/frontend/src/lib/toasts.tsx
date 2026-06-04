import {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useEffect,
	useRef,
	useState,
} from "react";
import { cn } from "@/lib/cn";

export type ToastTone = "info" | "success" | "error";

export interface Toast {
	id: number;
	message: string;
	tone: ToastTone;
	durationMs: number;
}

interface ToastsContextValue {
	toast: (message: string, options?: Partial<Toast>) => number;
	dismiss: (id: number) => void;
}

const ToastsContext = createContext<ToastsContextValue | null>(null);
let _id = 0;

export function ToastsProvider({ children }: { children: ReactNode }) {
	const [items, setItems] = useState<Toast[]>([]);
	const timers = useRef(new Map<number, number>());

	const dismiss = useCallback((id: number) => {
		setItems((prev) => prev.filter((t) => t.id !== id));
		const timer = timers.current.get(id);
		if (timer) {
			window.clearTimeout(timer);
			timers.current.delete(id);
		}
	}, []);

	const toast = useCallback(
		(message: string, options: Partial<Toast> = {}): number => {
			const id = ++_id;
			const item: Toast = {
				id,
				message,
				tone: options.tone ?? "info",
				durationMs: options.durationMs ?? 4500,
			};
			setItems((prev) => [...prev, item]);
			timers.current.set(
				id,
				window.setTimeout(() => dismiss(id), item.durationMs),
			);
			return id;
		},
		[dismiss],
	);

	useEffect(() => {
		const t = timers.current;
		return () => {
			for (const id of t.values()) window.clearTimeout(id);
		};
	}, []);

	return (
		<ToastsContext.Provider value={{ toast, dismiss }}>
			{children}
			<div
				aria-live="polite"
				aria-atomic="false"
				className="fixed bottom-4 right-4 z-50 flex flex-col gap-2"
			>
				{items.map((t) => (
					<div
						key={t.id}
						role="status"
						className={cn(
							"min-w-[240px] max-w-sm border bg-bg-elevated px-4 py-2 text-sm shadow-lg",
							t.tone === "info" && "border-border-strong text-fg",
							t.tone === "success" && "border-fg text-fg",
							t.tone === "error" && "border-fg bg-fg text-bg",
						)}
					>
						<button
							type="button"
							onClick={() => dismiss(t.id)}
							className="float-right -mr-2 -mt-1 px-2 text-fg-subtle hover:text-fg"
							aria-label="Dismiss"
						>
							×
						</button>
						{t.message}
					</div>
				))}
			</div>
		</ToastsContext.Provider>
	);
}

export function useToasts(): ToastsContextValue {
	const ctx = useContext(ToastsContext);
	if (!ctx) throw new Error("useToasts must be used inside <ToastsProvider>");
	return ctx;
}
