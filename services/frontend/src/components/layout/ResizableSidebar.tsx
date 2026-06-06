import {
	type CSSProperties,
	type ReactNode,
	type PointerEvent as RPointerEvent,
	useCallback,
	useEffect,
	useRef,
	useState,
} from "react";
import { cn } from "@/lib/cn";
import { useLocalStorageState } from "@/lib/useLocalStorage";

/**
 * Sidebar that:
 *
 *   - Persists its width to localStorage (one key per id).
 *   - Resizes via a 5 px hit-zone on its right edge — drag to adjust;
 *     double-click to reset to default.
 *   - Collapses to a thin icon-only rail (or fully off-screen on mobile).
 *     The collapsed state is persisted alongside the width.
 *   - On screens narrower than the `mobileBreakpointPx`, the sidebar
 *     becomes a drawer with the mobile backdrop instead of a fixed rail.
 */
interface ResizableSidebarProps {
	/** localStorage key prefix — distinguishes app vs chat sidebars. */
	id: string;
	/** Sidebar contents. Receives:
	 *   - `collapsed`        — render icon-only vs full-width
	 *   - `width`            — effective px width
	 *   - `toggleCollapsed`  — let the caller place the collapse
	 *                          control wherever makes sense for its
	 *                          layout instead of relying on an
	 *                          absolute-positioned button that might
	 *                          overlap other footer chrome.
	 */
	children: (state: {
		collapsed: boolean;
		width: number;
		toggleCollapsed: () => void;
	}) => ReactNode;
	defaultWidth?: number;
	minWidth?: number;
	maxWidth?: number;
	collapsedWidth?: number;
	mobileOpen: boolean;
	onMobileClose: () => void;
	mobileBreakpointPx?: number;
	className?: string;
	"aria-label": string;
}

const PERSIST_WIDTH = "dequorum.sidebar.width";
const PERSIST_COLLAPSED = "dequorum.sidebar.collapsed";

export function ResizableSidebar({
	id,
	children,
	defaultWidth = 264,
	minWidth = 200,
	maxWidth = 420,
	collapsedWidth = 56,
	mobileOpen,
	onMobileClose,
	mobileBreakpointPx = 768,
	className,
	"aria-label": ariaLabel,
}: ResizableSidebarProps) {
	const [width, setWidth] = useLocalStorageState<number>(`${PERSIST_WIDTH}.${id}`, defaultWidth);
	const [collapsed, setCollapsed] = useLocalStorageState<boolean>(
		`${PERSIST_COLLAPSED}.${id}`,
		false,
	);
	const [isMobile, setIsMobile] = useState(false);
	const [isDragging, setIsDragging] = useState(false);
	const draggingRef = useRef(false);
	const asideRef = useRef<HTMLElement>(null);

	useEffect(() => {
		const mq = window.matchMedia(`(max-width: ${mobileBreakpointPx - 1}px)`);
		const onChange = () => setIsMobile(mq.matches);
		onChange();
		mq.addEventListener("change", onChange);
		return () => mq.removeEventListener("change", onChange);
	}, [mobileBreakpointPx]);

	// Drag-to-resize.
	//
	// Two non-obvious things to get right:
	//
	// 1. `e.clientX` is viewport-relative. The new width is
	//    `clientX − sidebar's left edge` — otherwise sidebars that don't
	//    start at x=0 (e.g. the chat-sessions sidebar sitting to the
	//    right of the app nav rail) inflate their width by the offset
	//    and feel laggy/unresponsive as the cursor moves.
	//
	// 2. Width transitions are great for the collapse animation but
	//    catastrophic during drag — they smear every pointermove over
	//    200ms, producing visible cursor-lag. Flip `isDragging` on
	//    pointer-down so the CSS transition disables for the duration
	//    of the drag.
	const onPointerDown = useCallback(
		(e: RPointerEvent<HTMLDivElement>) => {
			if (collapsed || isMobile) return;
			e.preventDefault();
			(e.target as Element).setPointerCapture(e.pointerId);
			draggingRef.current = true;
			setIsDragging(true);
			document.body.style.cursor = "ew-resize";
			document.body.style.userSelect = "none";
		},
		[collapsed, isMobile],
	);
	const onPointerMove = useCallback(
		(e: RPointerEvent<HTMLDivElement>) => {
			if (!draggingRef.current) return;
			const leftEdge = asideRef.current?.getBoundingClientRect().left ?? 0;
			const raw = e.clientX - leftEdge;
			const next = Math.min(maxWidth, Math.max(minWidth, raw));
			setWidth(next);
		},
		[minWidth, maxWidth, setWidth],
	);
	const endDrag = useCallback((e: RPointerEvent<HTMLDivElement>) => {
		if (!draggingRef.current) return;
		(e.target as Element).releasePointerCapture(e.pointerId);
		draggingRef.current = false;
		setIsDragging(false);
		document.body.style.cursor = "";
		document.body.style.userSelect = "";
	}, []);

	const effectiveWidth = collapsed ? collapsedWidth : width;
	const style: CSSProperties = isMobile ? { width: width } : { width: effectiveWidth };

	return (
		<>
			{isMobile && mobileOpen && (
				<button
					type="button"
					aria-label="Close menu"
					onClick={onMobileClose}
					className="fixed inset-0 z-30 bg-bg/70 backdrop-blur-sm md:hidden"
				/>
			)}
			<aside
				ref={asideRef}
				aria-label={ariaLabel}
				style={style}
				className={cn(
					"relative flex shrink-0 flex-col border-r border-border bg-bg-elevated",
					// Smooth collapse/expand via CSS transition — but only
					// when NOT dragging, otherwise width updates smear over
					// 200ms and the cursor visibly leads the sidebar edge.
					!isDragging && "transition-[width] duration-200 ease-out",
					isMobile
						? cn(
								"fixed inset-y-0 left-0 z-40 transform",
								mobileOpen ? "translate-x-0" : "-translate-x-full",
							)
						: "",
					className,
				)}
			>
				{children({
					collapsed,
					width: effectiveWidth,
					toggleCollapsed: () => setCollapsed((v) => !v),
				})}

				{/* Right-edge drag handle — desktop only, hidden when collapsed.
				 * Keyboard accessible: focusable, with ARIA value props and
				 * arrow-key resize. */}
				{!isMobile && !collapsed && (
					<div
						role="separator"
						aria-orientation="vertical"
						aria-label="Resize sidebar"
						aria-valuenow={Math.round(width)}
						aria-valuemin={minWidth}
						aria-valuemax={maxWidth}
						tabIndex={0}
						onPointerDown={onPointerDown}
						onPointerMove={onPointerMove}
						onPointerUp={endDrag}
						onPointerCancel={endDrag}
						onDoubleClick={() => setWidth(defaultWidth)}
						onKeyDown={(e) => {
							// Arrow keys nudge the width 10px at a time; Home/End
							// snap to min/max. Lets keyboard users do everything
							// the pointer can.
							const step = e.shiftKey ? 40 : 10;
							if (e.key === "ArrowLeft") {
								e.preventDefault();
								setWidth(Math.max(minWidth, width - step));
							} else if (e.key === "ArrowRight") {
								e.preventDefault();
								setWidth(Math.min(maxWidth, width + step));
							} else if (e.key === "Home") {
								e.preventDefault();
								setWidth(minWidth);
							} else if (e.key === "End") {
								e.preventDefault();
								setWidth(maxWidth);
							}
						}}
						className="group absolute -right-1 top-0 h-full w-2 cursor-ew-resize focus:outline-none focus-visible:ring-2 focus-visible:ring-fg-muted/40"
					>
						<span className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-transparent transition-colors group-hover:bg-fg-subtle/40" />
					</div>
				)}
			</aside>
		</>
	);
}
