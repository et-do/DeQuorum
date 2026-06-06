import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

/**
 * Landing-page hero: animated network mesh + a narrative overlay.
 *
 * One coordinated component (canvas + React labels) so the packets you
 * see flying across the mesh are the *actual* packets the corner labels
 * are describing — not random ambient activity.
 *
 * Each "story" plays out in 4 beats, each ~3.5 s long. Concrete actors
 * are picked per story:
 *
 *   - **user** — one front-facing node
 *   - **responders** — 3 of the user's edge-connected neighbors
 *   - **contributor** — a node further out, neighbor of an responder
 *   - **host** — one of the responder nodes (where compute runs)
 *
 * Beats:
 *
 *   0  ask         user node pulses (incoming question)
 *   1  route       3 query packets travel user → responders; responders flash
 *   2  cite        citation packet responder → contributor; contributor
 *                  flashes; response packet contributor → user; user
 *                  flashes
 *   3  settle      tiny payment packets user → contributor, user → host
 *
 * Background random pulses also fire at a low rate between stories so
 * the mesh feels alive (but never overlap in volume with the story).
 *
 * Decorative only. Honors `prefers-reduced-motion` (rotation freezes
 * and no new pulses; the React label component skips rendering).
 */

const NODES = 80;
const EDGE_THRESHOLD = 0.55;
const ROTATION_SPEED = 0.0012;
const STEP_MS = 3500;
const GAP_MS = 1800;
const FADE_MS = 500;
/**
 * Delay between the node burst firing and the label/lines for that beat
 * appearing. Reads as: node "collides", then a moment later the text
 * box + connection line resolve to explain what just happened.
 */
const LABEL_DELAY_MS = 280;

type Role = "user" | "responder" | "contributor" | "host";

/**
 * Per-role visual config for bursts + connection lines. Monochrome but
 * distinguished by size + line weight + an optional outer halo so each
 * role reads as a different "kind of event" at a glance.
 */
const ROLE_STYLE: Record<Role, { maxR: number; lineW: number; halo: boolean; lineDash: number[] }> =
	{
		user: { maxR: 40, lineW: 2.0, halo: false, lineDash: [] },
		responder: { maxR: 24, lineW: 1.0, halo: false, lineDash: [] },
		contributor: { maxR: 32, lineW: 1.5, halo: true, lineDash: [] },
		// Host line was dashed to "differentiate compute provider" but at
		// this visual scale it read as broken/dotted, not semantic.
		// Same solid stroke, slightly thinner — distinction comes from
		// the smaller burst radius alone.
		host: { maxR: 22, lineW: 0.8, halo: false, lineDash: [] },
	};

interface Point3 {
	x: number;
	y: number;
	z: number;
}

type Kind = "query" | "answer" | "settle" | "ambient";

interface Packet {
	from: number;
	to: number;
	progress: number;
	speed: number;
	kind: Kind;
	/** Fired once when `progress` first crosses 1.0. Lets the story
	 * driver wait for "the packet actually got there" before bursting
	 * the target node and showing the label — so text appears after
	 * the traversal lands, not before it has even started. */
	onArrive?: () => void;
}

interface Actors {
	user: number;
	/** Background nodes that briefly light up while the router narrows
	 * the search space — they represent the routed category's partition,
	 * not any kind of persona or expert layer. */
	responders: number[];
	/** The contributor whose approved contribution(s) ended up in the
	 * retrieval set for this question. */
	contributor: number;
	/** A compute host serving the inference for this query. */
	host: number;
}

interface Story {
	user: string;
	question: string;
	/** The taxonomy category the question routes into. Phrased as a
	 * leaf-style id so it reads like real product copy. */
	category: string;
	contributor: string;
	cited: string;
}

const STORIES: Story[] = [
	{
		user: "Sam",
		question: "asks about long-COVID brain fog",
		category: "medicine / neurology / post-viral",
		contributor: "Dr. Chen",
		cited: "Dr. Chen's review of post-viral cognitive symptoms",
	},
	{
		user: "Priya",
		question: "asks how to rebalance her 401(k)",
		category: "finance / personal / retirement-planning",
		contributor: "Eli",
		cited: "Eli's analysis of glidepath strategies",
	},
	{
		user: "Jordan",
		question: "asks about lithium mining's water cost",
		category: "climate / extraction / lithium",
		contributor: "Anya",
		cited: "Anya's field study from Salar de Atacama",
	},
	{
		user: "Marisol",
		question: "asks why her sourdough won't rise",
		category: "cooking / fermentation / sourdough",
		contributor: "Tomás",
		cited: "Tomás's notes on starter hydration",
	},
	{
		user: "Devon",
		question: "asks how Bauhaus influenced product design",
		category: "design / history / modernism",
		contributor: "Yuki",
		cited: "Yuki's essays on Ulm School lineage",
	},
	{
		user: "Hana",
		question: "asks when to see a cardiologist about chest pain",
		category: "medicine / cardiology / triage",
		contributor: "Dr. Okafor",
		cited: "Dr. Okafor's triage guidelines",
	},
	{
		user: "Theo",
		question: "asks what's underrated to see in Lisbon",
		category: "travel / Portugal / Lisbon",
		contributor: "Inês",
		cited: "Inês's neighborhood walking guide",
	},
];

function spherePoints(count: number): Point3[] {
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

/**
 * A line connecting two nodes that a packet has traveled along during
 * the current story. Stays visible (and accumulates with other traces
 * from the same story) so the viewer sees the whole traversed path,
 * not just the moving dot. Fades to 0 between stories.
 */
interface TraceLine {
	from: number;
	to: number;
	role: Role;
	/** Build-up coefficient — ramps to 1 as the corresponding packet
	 * travels, holds at 1 while the story is active, fades to 0 once
	 * the story resets. */
	alpha: number;
	target: number;
}

interface State {
	points: Point3[];
	adjacency: number[][];
	edges: [number, number, number][];
	packets: Packet[];
	nodeFlash: Float32Array;
	/** Per-node sustained pulse (e.g., user node during step 0). Refreshed
	 * each frame while the source is "active"; decays once released. */
	nodePulse: Float32Array;
	/** Per-node "burst" — instant expanding ring fired the moment a beat
	 * begins to visually punctuate the label appearing. Lasts ~0.5s. */
	nodeBurst: Float32Array;
	nodeBurstAge: Float32Array;
	/** Per-slot connection-line opacity, eased each frame toward the
	 * target value based on which beat is active. */
	lineAlpha: { tl: number; tr: number; br: number; bl: number };
	/** Persistent node-to-node traces for the current story. */
	traces: TraceLine[];
	rotation: number;
	actors: Actors | null;
}

function roleOf(actors: Actors | null, idx: number): Role | null {
	if (!actors) return null;
	// Order matters: host overrides responder (since host ∈ responders).
	if (idx === actors.user) return "user";
	if (idx === actors.contributor) return "contributor";
	if (idx === actors.host) return "host";
	if (actors.responders.includes(idx)) return "responder";
	return null;
}

function pickActors(state: State): Actors {
	const { points, adjacency } = state;
	// User: a node on the front face (z > 0) so it's visible at story start.
	// Try a few random candidates, fall back to any node with enough neighbors.
	let user = -1;
	for (let tries = 0; tries < 30 && user < 0; tries++) {
		const cand = Math.floor(Math.random() * points.length);
		if (points[cand]!.z > 0.1 && adjacency[cand]!.length >= 3) user = cand;
	}
	if (user < 0) {
		user = points.findIndex((_, i) => adjacency[i]!.length >= 3);
		if (user < 0) user = 0;
	}

	// Experts: 3 neighbors of user.
	const userNeighbors = adjacency[user]!.slice();
	shuffle(userNeighbors);
	const responders = userNeighbors.slice(0, Math.min(3, userNeighbors.length));

	// Contributor: a neighbor of one of the responders that isn't user/responders.
	const used = new Set([user, ...responders]);
	let contributor = -1;
	for (const e of responders) {
		const cands = adjacency[e]!.filter((n) => !used.has(n));
		if (cands.length > 0) {
			contributor = cands[Math.floor(Math.random() * cands.length)]!;
			break;
		}
	}
	// Fallback: any non-used node.
	if (contributor < 0) {
		for (let i = 0; i < points.length; i++) {
			if (!used.has(i)) {
				contributor = i;
				break;
			}
		}
	}

	// Host: one of the responders (the node where compute physically runs).
	const host = responders[Math.floor(Math.random() * responders.length)] ?? user;

	return { user, responders, contributor, host };
}

function shuffle<T>(arr: T[]): void {
	for (let i = arr.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1));
		[arr[i], arr[j]] = [arr[j]!, arr[i]!];
	}
}

export function NetworkVisualization({ className }: { className?: string }) {
	const canvasRef = useRef<HTMLCanvasElement>(null);
	const stateRef = useRef<State | null>(null);
	// Mirror currentStep into a ref so the raf loop can read it without
	// re-running its effect.
	const stepRef = useRef<number>(-1);
	const [currentStory, setCurrentStory] = useState<Story | null>(null);
	const [currentStep, setCurrentStep] = useState<number>(-1);
	useEffect(() => {
		stepRef.current = currentStep;
	}, [currentStep]);

	// --- canvas + animation loop ---
	useEffect(() => {
		const canvas = canvasRef.current;
		if (!canvas) return;
		const ctx = canvas.getContext("2d");
		if (!ctx) return;

		const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

		// Build mesh state once.
		const points = spherePoints(NODES);
		const edges: [number, number, number][] = [];
		const adjacency: number[][] = Array.from({ length: points.length }, () => []);
		for (let i = 0; i < points.length; i++) {
			for (let j = i + 1; j < points.length; j++) {
				const dx = points[i]!.x - points[j]!.x;
				const dy = points[i]!.y - points[j]!.y;
				const dz = points[i]!.z - points[j]!.z;
				const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
				if (d < EDGE_THRESHOLD) {
					edges.push([i, j, d]);
					adjacency[i]!.push(j);
					adjacency[j]!.push(i);
				}
			}
		}

		stateRef.current = {
			points,
			adjacency,
			edges,
			packets: [],
			nodeFlash: new Float32Array(points.length),
			nodePulse: new Float32Array(points.length),
			nodeBurst: new Float32Array(points.length),
			nodeBurstAge: new Float32Array(points.length),
			lineAlpha: { tl: 0, tr: 0, br: 0, bl: 0 },
			traces: [],
			rotation: 0,
			actors: null,
		};

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

		let raf = 0;
		let lastSize = { w: 0, h: 0, dpr: 1 };

		const render = () => {
			const dpr = window.devicePixelRatio || 1;
			const cw = canvas.clientWidth;
			const ch = canvas.clientHeight;
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

			const state = stateRef.current!;
			const radius = Math.min(cw, ch) * 0.42;
			const cx = cw / 2;
			const cy = ch / 2;
			const [r, g, b] = fg;
			ctx.lineWidth = 1;

			const sin = Math.sin(state.rotation);
			const cos = Math.cos(state.rotation);
			const projected = state.points.map((p) => {
				const rx = p.x * cos - p.z * sin;
				const rz = p.x * sin + p.z * cos;
				const persp = 1 / (1.6 - rz * 0.4);
				return {
					x: cx + rx * radius * persp,
					y: cy + p.y * radius * persp,
					z: rz,
				};
			});

			// Edges.
			for (const [i, j, d] of state.edges) {
				const a = projected[i]!;
				const b2 = projected[j]!;
				const depth = (a.z + b2.z) * 0.5;
				const depthAlpha = 0.45 + depth * 0.5;
				const distAlpha = 1 - d / EDGE_THRESHOLD;
				const alpha = Math.max(0, depthAlpha * distAlpha * 0.65);
				ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
				ctx.beginPath();
				ctx.moveTo(a.x, a.y);
				ctx.lineTo(b2.x, b2.y);
				ctx.stroke();
			}

			// Connection lines from each label slot to the actor node(s) it
			// names. Each line's alpha eases toward 1 once its beat starts
			// and back to 0 when the story ends. The line endpoint on the
			// mesh side rotates with the sphere, so the label visibly
			// "tracks" its node.
			const step = stepRef.current;
			const actors = state.actors;
			if (actors) {
				const slotPad = Math.max(48, Math.min(cw, ch) * 0.1);
				const slot = {
					tl: { x: slotPad, y: slotPad },
					tr: { x: cw - slotPad, y: slotPad },
					br: { x: cw - slotPad, y: ch - slotPad },
					bl: { x: slotPad, y: ch - slotPad },
				};

				const targets = {
					tl: step >= 0 ? 1 : 0,
					tr: step >= 1 ? 1 : 0,
					br: step >= 2 ? 1 : 0,
					bl: step >= 3 ? 1 : 0,
				};
				const la = state.lineAlpha;
				la.tl += (targets.tl - la.tl) * 0.08;
				la.tr += (targets.tr - la.tr) * 0.08;
				la.br += (targets.br - la.br) * 0.08;
				la.bl += (targets.bl - la.bl) * 0.08;

				const line = (
					from: { x: number; y: number },
					to: { x: number; y: number },
					alpha: number,
					role: Role,
				) => {
					if (alpha < 0.03) return;
					const style = ROLE_STYLE[role];
					ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.6})`;
					ctx.lineWidth = style.lineW * 0.7;
					if (style.lineDash.length > 0) ctx.setLineDash(style.lineDash);
					ctx.beginPath();
					ctx.moveTo(from.x, from.y);
					ctx.lineTo(to.x, to.y);
					ctx.stroke();
					if (style.lineDash.length > 0) ctx.setLineDash([]);
					ctx.lineWidth = 1;
					// Small tick at the node end so the line "lands".
					ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.7})`;
					ctx.beginPath();
					ctx.arc(to.x, to.y, 2.5, 0, Math.PI * 2);
					ctx.fill();
				};

				line(slot.tl, projected[actors.user]!, la.tl, "user");
				for (const responder of actors.responders) {
					line(slot.tr, projected[responder]!, la.tr * 0.85, "responder");
				}
				line(slot.br, projected[actors.contributor]!, la.br, "contributor");
				// Payments fan out to BOTH the contributor (solid, normal) and
				// the host (dashed, lighter) — distinguishes "data provider"
				// from "compute provider" at a glance.
				line(slot.bl, projected[actors.contributor]!, la.bl * 0.85, "contributor");
				line(slot.bl, projected[actors.host]!, la.bl * 0.85, "host");
			}

			// Nodes + flash + sustained pulse + burst.
			for (let i = 0; i < projected.length; i++) {
				const p = projected[i]!;
				const depthAmt = 0.5 + p.z * 0.5;
				const alpha = 0.45 + depthAmt * 0.55;
				ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
				ctx.beginPath();
				ctx.arc(p.x, p.y, 1.2 + depthAmt * 1.6, 0, Math.PI * 2);
				ctx.fill();

				// Burst — an expanding ring + bright inner disk that fires the
				// instant a beat starts. Sized per role so each kind of event
				// reads as a different "kind of thing":
				//   user        — biggest, thick stroke (protagonist)
				//   contributor — medium with a faint outer halo (knowledge source)
				//   responder      — medium, plain
				//   host        — smaller (background actor)
				const burst = state.nodeBurst[i]!;
				if (burst > 0.01) {
					const role = roleOf(state.actors, i);
					const style = role ? ROLE_STYLE[role] : ROLE_STYLE.responder;
					const age = state.nodeBurstAge[i]!;
					const phase = Math.min(1, age / 30);
					const ringR = 6 + phase * (style.maxR - 6);
					const ringA = burst * (1 - phase) * 0.8;
					ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${ringA})`;
					ctx.lineWidth = style.lineW;
					ctx.beginPath();
					ctx.arc(p.x, p.y, ringR, 0, Math.PI * 2);
					ctx.stroke();
					// Optional outer halo (contributor) — wider, fainter ring
					// trailing the main one so the cited node has a unique
					// "echo" silhouette.
					if (style.halo) {
						const haloR = ringR + 14;
						ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${ringA * 0.35})`;
						ctx.lineWidth = 1;
						ctx.beginPath();
						ctx.arc(p.x, p.y, haloR, 0, Math.PI * 2);
						ctx.stroke();
					}
					ctx.lineWidth = 1;
					ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${burst * (1 - phase * 0.5) * 0.6})`;
					ctx.beginPath();
					ctx.arc(p.x, p.y, 3.5 + (1 - phase) * 3, 0, Math.PI * 2);
					ctx.fill();
					state.nodeBurstAge[i] = age + 1;
					if (age > 30) {
						state.nodeBurst[i] = 0;
						state.nodeBurstAge[i] = 0;
					}
				}

				const flash = state.nodeFlash[i]!;
				if (flash > 0.01) {
					ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${flash * 0.35})`;
					ctx.beginPath();
					ctx.arc(p.x, p.y, 3 + flash * 10, 0, Math.PI * 2);
					ctx.fill();
					state.nodeFlash[i] = flash * 0.9;
				}
				const pulse = state.nodePulse[i]!;
				if (pulse > 0.01) {
					const t = state.rotation * 100;
					const breathe = 0.5 + 0.5 * Math.sin(t * 2);
					ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${pulse * (0.12 + breathe * 0.1)})`;
					ctx.beginPath();
					ctx.arc(p.x, p.y, 6 + breathe * 6, 0, Math.PI * 2);
					ctx.fill();
				}
			}

			// Persistent story traces — the cumulative path the story
			// has walked. Each trace eases toward its target alpha each
			// frame; story end sets target to 0 so they fade together
			// instead of snapping off.
			for (let k = state.traces.length - 1; k >= 0; k--) {
				const tr = state.traces[k]!;
				tr.alpha += (tr.target - tr.alpha) * 0.06;
				if (tr.target === 0 && tr.alpha < 0.01) {
					state.traces.splice(k, 1);
					continue;
				}
				const a = projected[tr.from]!;
				const b2 = projected[tr.to]!;
				const depth = (a.z + b2.z) * 0.5;
				const visible = tr.alpha * (0.5 + depth * 0.5);
				if (visible < 0.01) continue;
				ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${visible * 0.55})`;
				ctx.lineWidth = 1.2;
				ctx.beginPath();
				ctx.moveTo(a.x, a.y);
				ctx.lineTo(b2.x, b2.y);
				ctx.stroke();
				ctx.lineWidth = 1;
			}

			// Packets.
			for (let k = state.packets.length - 1; k >= 0; k--) {
				const pkt = state.packets[k]!;
				const a = projected[pkt.from]!;
				const b2 = projected[pkt.to]!;
				const t = pkt.progress;
				const x = a.x * (1 - t) + b2.x * t;
				const y = a.y * (1 - t) + b2.y * t;
				const zMid = (a.z + b2.z) * 0.5;
				const depthAlpha = Math.max(0, 0.4 + zMid * 0.6);

				const cfg = (() => {
					switch (pkt.kind) {
						case "query":
							return { size: 2.6, alpha: 1.0 * depthAlpha, trail: 6 };
						case "answer":
							return { size: 2.2, alpha: 0.9 * depthAlpha, trail: 5 };
						case "settle":
							return { size: 1.5, alpha: 0.7 * depthAlpha, trail: 3 };
						case "ambient":
							return { size: 1.4, alpha: 0.5 * depthAlpha, trail: 3 };
					}
				})();

				for (let s = 1; s <= cfg.trail; s++) {
					const tt = t - s * 0.04;
					if (tt < 0) break;
					const tx = a.x * (1 - tt) + b2.x * tt;
					const ty = a.y * (1 - tt) + b2.y * tt;
					ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${cfg.alpha * (1 - s / (cfg.trail + 1)) * 0.5})`;
					ctx.beginPath();
					ctx.arc(tx, ty, cfg.size * 0.6, 0, Math.PI * 2);
					ctx.fill();
				}
				ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${cfg.alpha})`;
				ctx.beginPath();
				ctx.arc(x, y, cfg.size, 0, Math.PI * 2);
				ctx.fill();

				pkt.progress += pkt.speed;
				if (pkt.progress >= 1) {
					state.nodeFlash[pkt.to] = 1;
					pkt.onArrive?.();
					state.packets.splice(k, 1);
				}
			}

			// (No ambient packets. Random pulses on unrelated nodes
			// distracted from the story line; the mesh stays calm
			// between stories instead.)

			if (!reduced) state.rotation += ROTATION_SPEED;
			raf = requestAnimationFrame(render);
		};
		raf = requestAnimationFrame(render);
		return () => {
			cancelAnimationFrame(raf);
			themeObserver.disconnect();
		};
	}, []);

	// --- story scheduler: drives both label state and packet emissions ---
	useEffect(() => {
		const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
		if (reduced) return;

		let cancelled = false;
		let storyIdx = Math.floor(Math.random() * STORIES.length);

		// Wait for the canvas effect to populate stateRef.
		async function waitForState() {
			while (!stateRef.current && !cancelled) await sleep(50);
		}

		function burst(state: State, nodeIdx: number) {
			state.nodeBurst[nodeIdx] = 1;
			state.nodeBurstAge[nodeIdx] = 0;
			state.nodeFlash[nodeIdx] = Math.max(state.nodeFlash[nodeIdx]!, 0.9);
		}

		function resetLineAlphas(state: State) {
			state.lineAlpha.tl = 0;
			state.lineAlpha.tr = 0;
			state.lineAlpha.br = 0;
			state.lineAlpha.bl = 0;
		}

		/**
		 * Punch the mesh first, THEN advance the step (which fades the
		 * label + lines in). For beats with no traversal (the user is
		 * the origin), this is the right entry point.
		 */
		async function punchThenLabel(state: State, nodes: number[], step: number) {
			for (const n of nodes) burst(state, n);
			await sleep(LABEL_DELAY_MS);
			if (cancelled) return;
			setCurrentStep(step);
		}

		/**
		 * Send packets from origin → each target, wait until they ALL
		 * arrive, THEN punch the targets and advance the step. Reading
		 * order becomes: data travels → arrives with a punch → text +
		 * connection line explain what just happened.
		 *
		 * The packet-arrival callback fires from inside the canvas raf
		 * loop, so we wrap each push into a Promise resolved on arrival.
		 */
		async function traverseThenLabel(
			state: State,
			from: number,
			targets: number[],
			step: number,
			kind: Kind = "query",
			speed = 0.022,
			traceRole: Role = "responder",
		): Promise<void> {
			const arrivals = targets.map((to) => {
				// Push a persistent trace line that lights up to 1 as
				// the packet travels. The trace lingers (target stays at
				// 1) until the story resets — see resetTraces() at the
				// bottom of playOnce.
				state.traces.push({
					from,
					to,
					role: traceRole,
					alpha: 0,
					target: 1,
				});
				return new Promise<void>((resolve) => {
					state.packets.push({
						from,
						to,
						progress: 0,
						speed,
						kind,
						onArrive: resolve,
					});
				});
			});
			await Promise.all(arrivals);
			if (cancelled) return;
			for (const t of targets) burst(state, t);
			await sleep(LABEL_DELAY_MS);
			if (cancelled) return;
			setCurrentStep(step);
		}

		function fadeTraces(state: State) {
			for (const tr of state.traces) tr.target = 0;
		}

		/** Estimated packet travel + label delay so we can budget the
		 * post-label dwell against the total step duration. ~750ms at
		 * speed=0.022 + LABEL_DELAY_MS. */
		const TRAVEL_BUDGET_MS = 750 + LABEL_DELAY_MS;
		const BEAT_TAIL_MS = STEP_MS - LABEL_DELAY_MS;
		const BEAT_TAIL_AFTER_TRAVEL_MS = Math.max(800, STEP_MS - TRAVEL_BUDGET_MS);

		async function playOnce() {
			const state = stateRef.current!;
			const story = STORIES[storyIdx % STORIES.length]!;
			storyIdx += 1;

			const actors = pickActors(state);
			state.actors = actors;
			// Snap corner-label alphas + clear leftover traces so a new
			// story doesn't render against the prior story's lines or
			// inherit any fade-out residue.
			resetLineAlphas(state);
			state.traces = [];

			// --- Beat 0 — ask ---
			setCurrentStory(story);
			await punchThenLabel(state, [actors.user], 0);
			const sustainEnd0 = performance.now() + BEAT_TAIL_MS;
			const sustainTick = () => {
				if (!stateRef.current || cancelled) return;
				if (performance.now() > sustainEnd0) return;
				stateRef.current.nodePulse[actors.user] = 1;
				window.setTimeout(sustainTick, 50);
			};
			sustainTick();
			await sleep(BEAT_TAIL_MS);

			// --- Beat 1 — route ---
			state.nodePulse[actors.user] = 0;
			await traverseThenLabel(
				state,
				actors.user,
				actors.responders,
				1,
				"query",
				0.022,
				"responder",
			);
			await sleep(BEAT_TAIL_AFTER_TRAVEL_MS);

			// --- Beat 2 — cite ---
			const lookupExpert =
				actors.responders[Math.floor(Math.random() * actors.responders.length)] ?? actors.user;
			await traverseThenLabel(
				state,
				lookupExpert,
				[actors.contributor],
				2,
				"query",
				0.022,
				"contributor",
			);
			// Answer travels back to the user as a separate trace +
			// packet. The trace persists with the rest of the story so
			// the round-trip path is visible.
			state.traces.push({
				from: actors.contributor,
				to: actors.user,
				role: "user",
				alpha: 0,
				target: 1,
			});
			state.packets.push({
				from: actors.contributor,
				to: actors.user,
				progress: 0,
				speed: 0.02,
				kind: "answer",
				onArrive: () => {
					if (stateRef.current) burst(stateRef.current, actors.user);
				},
			});
			await sleep(BEAT_TAIL_AFTER_TRAVEL_MS);

			// --- Beat 3 — settle ---
			await traverseThenLabel(
				state,
				actors.user,
				[actors.contributor, actors.host],
				3,
				"settle",
				0.018,
				"contributor",
			);
			await sleep(BEAT_TAIL_AFTER_TRAVEL_MS);

			// Clear story, snap corner-label lines, fade the persistent
			// traces (they ease to 0 over a few hundred ms inside the
			// raf loop), then brief pause + loop.
			setCurrentStory(null);
			setCurrentStep(-1);
			state.actors = null;
			resetLineAlphas(state);
			fadeTraces(state);
			await sleep(GAP_MS);
		}

		(async () => {
			await waitForState();
			while (!cancelled) {
				await playOnce();
			}
		})();
		return () => {
			cancelled = true;
		};
	}, []);

	return (
		<div className={cn("relative h-full w-full", className)}>
			<canvas
				ref={canvasRef}
				role="presentation"
				aria-hidden="true"
				className="block h-full w-full text-fg min-h-[220px]"
			/>
			<ActivityLabels story={currentStory} step={currentStep} />
		</div>
	);
}

// --- React labels ------------------------------------------------------

function buildLabel(
	story: Story,
	step: number,
): { slot: "tl" | "tr" | "br" | "bl"; text: string } | null {
	switch (step) {
		case 0:
			// Beat 0 — question lands. The query enters the network at
			// the user's node.
			return {
				slot: "tl",
				text: `${story.user} ${story.question}`,
			};
		case 1:
			// Beat 1 — the router partitions into a category. The visual
			// ripple represents the routed slice of the corpus.
			return {
				slot: "tr",
				text: `Routes to the ${story.category} category`,
			};
		case 2:
			// Beat 2 — retrieval pulls signed contributions from inside
			// that partition.
			return {
				slot: "br",
				text: `Grounded by ${story.cited}`,
			};
		case 3:
			// Beat 3 — the ledger fans payouts back to the contributor
			// and the compute host that served the answer.
			return {
				slot: "bl",
				text: `Pays ${story.contributor} and the host that served it`,
			};
		default:
			return null;
	}
}

function ActivityLabels({ story, step }: { story: Story | null; step: number }) {
	// Track the most-recent label for each slot; once shown, a label stays
	// for the remainder of the story (cumulative narrative), then all clear.
	const [labels, setLabels] = useState<Record<"tl" | "tr" | "br" | "bl", string | null>>({
		tl: null,
		tr: null,
		br: null,
		bl: null,
	});

	useEffect(() => {
		if (!story || step < 0) {
			setLabels({ tl: null, tr: null, br: null, bl: null });
			return;
		}
		const next = buildLabel(story, step);
		if (!next) return;
		setLabels((prev) => ({ ...prev, [next.slot]: next.text }));
	}, [story, step]);

	return (
		<div aria-hidden="true" className="pointer-events-none absolute inset-0 select-none">
			<Label slot="tl" text={labels.tl} />
			<Label slot="tr" text={labels.tr} />
			<Label slot="br" text={labels.br} />
			<Label slot="bl" text={labels.bl} />
		</div>
	);
}

const SLOT_CLASSES: Record<"tl" | "tr" | "br" | "bl", string> = {
	tl: "top-3 left-3 sm:top-5 sm:left-5",
	tr: "top-3 right-3 sm:top-5 sm:right-5",
	br: "bottom-3 right-3 sm:bottom-5 sm:right-5",
	bl: "bottom-3 left-3 sm:bottom-5 sm:left-5",
};

function Label({ slot, text }: { slot: "tl" | "tr" | "br" | "bl"; text: string | null }) {
	const [mounted, setMounted] = useState<string | null>(null);
	const [shown, setShown] = useState(false);

	useEffect(() => {
		if (text) {
			setMounted(text);
			requestAnimationFrame(() => requestAnimationFrame(() => setShown(true)));
		} else {
			setShown(false);
			const t = window.setTimeout(() => setMounted(null), FADE_MS);
			return () => window.clearTimeout(t);
		}
	}, [text]);

	if (!mounted) return null;
	return (
		<div
			className={cn(
				"absolute max-w-[11rem] border border-border-strong bg-bg/95 px-2.5 py-1.5 text-xs font-medium leading-snug text-fg backdrop-blur shadow-sm sm:text-sm",
				"transition-all duration-500 ease-out",
				SLOT_CLASSES[slot],
				shown ? "opacity-100 translate-y-0" : "opacity-0",
				shown ? "" : slot === "tl" || slot === "tr" ? "-translate-y-1" : "translate-y-1",
			)}
		>
			{mounted}
		</div>
	);
}

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => window.setTimeout(resolve, ms));
}
