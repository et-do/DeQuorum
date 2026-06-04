import { useEffect, useRef } from "react";
import { cn } from "@/lib/cn";

/**
 * Decorative rotating-mesh hero. ~80 points on a sphere, edges drawn
 * between any pair within a 3D distance threshold, opacity falls off
 * with distance. All rendering uses the canvas's computed `color`
 * (CSS `currentColor`), so it automatically inverts between light and
 * dark themes. Honors `prefers-reduced-motion` by freezing rotation.
 *
 * Pure decoration — `aria-hidden` + `role="presentation"`.
 */
interface NetworkMeshProps {
	className?: string;
	/** Sphere point count. Edges scale O(n^2); ~80 is a good ceiling. */
	nodes?: number;
	/** 3D distance threshold for drawing an edge between two points. */
	edgeThreshold?: number;
	/** Radians per frame. ~0.0012 = a full rotation in ~87 seconds at 60fps. */
	rotationSpeed?: number;
}

interface Point3 {
	x: number;
	y: number;
	z: number;
}

function spherePoints(count: number): Point3[] {
	// Fibonacci sphere — evenly spaced points on a unit sphere.
	const phi = Math.PI * (Math.sqrt(5) - 1);
	const out: Point3[] = [];
	for (let i = 0; i < count; i++) {
		const y = 1 - (i / (count - 1)) * 2;
		const radius = Math.sqrt(1 - y * y);
		const theta = phi * i;
		out.push({
			x: Math.cos(theta) * radius,
			y,
			z: Math.sin(theta) * radius,
		});
	}
	return out;
}

export function NetworkMesh({
	className,
	nodes = 80,
	edgeThreshold = 0.55,
	rotationSpeed = 0.0012,
}: NetworkMeshProps) {
	const canvasRef = useRef<HTMLCanvasElement>(null);

	useEffect(() => {
		const canvas = canvasRef.current;
		if (!canvas) return;
		const ctx = canvas.getContext("2d");
		if (!ctx) return;

		const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

		const points = spherePoints(nodes);
		const edges: [number, number, number][] = [];
		for (let i = 0; i < points.length; i++) {
			for (let j = i + 1; j < points.length; j++) {
				const dx = points[i]!.x - points[j]!.x;
				const dy = points[i]!.y - points[j]!.y;
				const dz = points[i]!.z - points[j]!.z;
				const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
				if (d < edgeThreshold) edges.push([i, j, d]);
			}
		}

		let rotation = 0;
		let raf = 0;
		let lastSize = { w: 0, h: 0, dpr: 1 };

		// Resolve the foreground color once, then re-resolve on theme change.
		// `getComputedStyle(canvas).color` returns rgb() — we parse to inject
		// alpha per stroke.
		const parseRgb = (color: string): [number, number, number] => {
			const m = color.match(/\d+/g);
			if (!m || m.length < 3) return [255, 255, 255];
			return [Number(m[0]), Number(m[1]), Number(m[2])];
		};
		let fg = parseRgb(window.getComputedStyle(canvas).color);
		const themeObserver = new MutationObserver(() => {
			fg = parseRgb(window.getComputedStyle(canvas).color);
		});
		themeObserver.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ["data-theme"],
		});

		const render = () => {
			const dpr = window.devicePixelRatio || 1;
			const cw = canvas.clientWidth;
			const ch = canvas.clientHeight;

			// Skip frames where the canvas has no layout yet (parent collapsed).
			if (cw === 0 || ch === 0) {
				raf = requestAnimationFrame(render);
				return;
			}

			if (lastSize.w !== cw || lastSize.h !== ch || lastSize.dpr !== dpr) {
				canvas.width = Math.round(cw * dpr);
				canvas.height = Math.round(ch * dpr);
				lastSize = { w: cw, h: ch, dpr };
			}
			ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
			ctx.clearRect(0, 0, cw, ch);

			const radius = Math.min(cw, ch) * 0.42;
			const cx = cw / 2;
			const cy = ch / 2;
			const [r, g, b] = fg;
			ctx.lineWidth = 1;

			// Project points: rotate around Y axis, apply mild perspective.
			const sin = Math.sin(rotation);
			const cos = Math.cos(rotation);
			const projected = points.map((p) => {
				const rx = p.x * cos - p.z * sin;
				const rz = p.x * sin + p.z * cos;
				const persp = 1 / (1.6 - rz * 0.4);
				return {
					x: cx + rx * radius * persp,
					y: cy + p.y * radius * persp,
					z: rz,
				};
			});

			// Edges: opacity from distance + depth (back-facing fades).
			for (const [i, j, d] of edges) {
				const a = projected[i]!;
				const b = projected[j]!;
				const depth = (a.z + b.z) * 0.5;
				const depthAlpha = 0.45 + depth * 0.5;
				const distAlpha = 1 - d / edgeThreshold;
				const alpha = Math.max(0, depthAlpha * distAlpha * 0.65);
				ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
				ctx.beginPath();
				ctx.moveTo(a.x, a.y);
				ctx.lineTo(b.x, b.y);
				ctx.stroke();
			}

			// Nodes: small dots, brighter when toward the viewer.
			for (const p of projected) {
				const depthAmt = 0.5 + p.z * 0.5;
				const alpha = 0.45 + depthAmt * 0.55;
				ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
				ctx.beginPath();
				ctx.arc(p.x, p.y, 1.2 + depthAmt * 1.6, 0, Math.PI * 2);
				ctx.fill();
			}

			if (!reduced) rotation += rotationSpeed;
			raf = requestAnimationFrame(render);
		};

		raf = requestAnimationFrame(render);
		return () => {
			cancelAnimationFrame(raf);
			themeObserver.disconnect();
		};
	}, [nodes, edgeThreshold, rotationSpeed]);

	return (
		<canvas
			ref={canvasRef}
			role="presentation"
			aria-hidden="true"
			className={cn(
				"block h-full w-full text-fg",
				// Failsafe minimum so the canvas can't collapse to 0px if a
				// parent forgets to set explicit dimensions.
				"min-h-[320px]",
				className,
			)}
		/>
	);
}
