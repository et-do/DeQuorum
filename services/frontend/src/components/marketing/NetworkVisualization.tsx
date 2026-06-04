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
 *   - **experts** — 3 of the user's edge-connected neighbors
 *   - **contributor** — a node further out, neighbor of an expert
 *   - **host** — one of the expert nodes (where compute runs)
 *
 * Beats:
 *
 *   0  ask         user node pulses (incoming question)
 *   1  route       3 query packets travel user → experts; experts flash
 *   2  cite        citation packet expert → contributor; contributor
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
}

interface Actors {
	user: number;
	experts: number[];
	contributor: number;
	host: number;
}

interface Story {
	user: string;
	question: string;
	domain: string;
	contributor: string;
	cited: string;
}

const STORIES: Story[] = [
	{
		user: "Sam",
		question: "asks about long-COVID brain fog",
		domain: "neurology + immunology experts",
		contributor: "Dr. Chen",
		cited: "Dr. Chen's review of post-viral cognitive symptoms",
	},
	{
		user: "Priya",
		question: "asks how to rebalance her 401(k)",
		domain: "retirement-planning experts",
		contributor: "Eli",
		cited: "Eli's analysis of glidepath strategies",
	},
	{
		user: "Jordan",
		question: "asks about lithium mining's water cost",
		domain: "environmental scientists",
		contributor: "Anya",
		cited: "Anya's field study from Salar de Atacama",
	},
	{
		user: "Marisol",
		question: "asks why her sourdough won't rise",
		domain: "fermentation bakers",
		contributor: "Tomás",
		cited: "Tomás's notes on starter hydration",
	},
	{
		user: "Devon",
		question: "asks how Bauhaus influenced product design",
		domain: "design historians",
		contributor: "Yuki",
		cited: "Yuki's essays on Ulm School lineage",
	},
	{
		user: "Hana",
		question: "asks when to see a cardiologist about chest pain",
		domain: "cardiology + primary-care experts",
		contributor: "Dr. Okafor",
		cited: "Dr. Okafor's triage guidelines",
	},
	{
		user: "Theo",
		question: "asks what's underrated to see in Lisbon",
		domain: "Portugal travel experts",
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
	rotation: number;
	actors: Actors | null;
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
	const experts = userNeighbors.slice(0, Math.min(3, userNeighbors.length));

	// Contributor: a neighbor of one of the experts that isn't user/experts.
	const used = new Set([user, ...experts]);
	let contributor = -1;
	for (const e of experts) {
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

	// Host: one of the experts (the node where compute physically runs).
	const host = experts[Math.floor(Math.random() * experts.length)] ?? user;

	return { user, experts, contributor, host };
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
		let untilAmbient = 90 + Math.floor(Math.random() * 60);

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
				) => {
					if (alpha < 0.03) return;
					ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.55})`;
					ctx.lineWidth = 1;
					ctx.beginPath();
					ctx.moveTo(from.x, from.y);
					ctx.lineTo(to.x, to.y);
					ctx.stroke();
					// Small tick at the node end so the line "lands".
					ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.7})`;
					ctx.beginPath();
					ctx.arc(to.x, to.y, 2.5, 0, Math.PI * 2);
					ctx.fill();
				};

				line(slot.tl, projected[actors.user]!, la.tl);
				// TR has three experts — draw a fan to all of them at reduced
				// alpha so the eye reads "routing to multiple targets" without
				// the lines being too heavy.
				for (const expert of actors.experts) {
					line(slot.tr, projected[expert]!, la.tr * 0.85);
				}
				line(slot.br, projected[actors.contributor]!, la.br);
				// Payments fan out to BOTH the contributor and the host.
				line(slot.bl, projected[actors.contributor]!, la.bl * 0.85);
				line(slot.bl, projected[actors.host]!, la.bl * 0.85);
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
				// instant a beat starts. The whole effect is ~0.5s, sized so
				// the user can't miss it in their peripheral vision while
				// reading the label.
				const burst = state.nodeBurst[i]!;
				if (burst > 0.01) {
					const age = state.nodeBurstAge[i]!;
					const phase = Math.min(1, age / 30);
					const ringR = 6 + phase * 28;
					const ringA = burst * (1 - phase) * 0.75;
					ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${ringA})`;
					ctx.lineWidth = 1.5;
					ctx.beginPath();
					ctx.arc(p.x, p.y, ringR, 0, Math.PI * 2);
					ctx.stroke();
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
					state.packets.splice(k, 1);
				}
			}

			// Background ambient pulses between stories so the mesh isn't
			// dead air. Rate is much lower than the story-driven activity.
			if (!reduced) {
				untilAmbient -= 1;
				if (untilAmbient <= 0) {
					const fromIdx = Math.floor(Math.random() * state.points.length);
					const neighbors = state.adjacency[fromIdx]!;
					if (neighbors.length > 0) {
						const toIdx = neighbors[Math.floor(Math.random() * neighbors.length)]!;
						state.packets.push({
							from: fromIdx,
							to: toIdx,
							progress: 0,
							speed: 0.015,
							kind: "ambient",
						});
					}
					untilAmbient = 150 + Math.floor(Math.random() * 120);
				}
			}

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
			// Pair with a node flash so the source also looks "hot" instantly.
			state.nodeFlash[nodeIdx] = Math.max(state.nodeFlash[nodeIdx]!, 0.9);
		}

		async function playOnce() {
			const state = stateRef.current!;
			const story = STORIES[storyIdx % STORIES.length]!;
			storyIdx += 1;

			const actors = pickActors(state);
			state.actors = actors;

			// --- Beat 0 — ask ---
			// Label TL fades in. Concurrently: burst on user node + sustained
			// breathing pulse on the user for the whole beat. The burst is
			// the visual "punch" the eye catches at the moment the label
			// appears; the sustained pulse keeps the user node clearly
			// identified as the "who" of the story.
			setCurrentStory(story);
			setCurrentStep(0);
			burst(state, actors.user);
			const sustainEnd0 = performance.now() + STEP_MS;
			const sustainTick = () => {
				if (!stateRef.current || cancelled) return;
				if (performance.now() > sustainEnd0) return;
				stateRef.current.nodePulse[actors.user] = 1;
				window.setTimeout(sustainTick, 50);
			};
			sustainTick();
			await sleep(STEP_MS);

			// --- Beat 1 — route ---
			// Label TR fades in. Concurrently: bursts on all three expert
			// nodes (the destinations the label names) AND fire the query
			// packets so the bursts "preview" where the packets are heading.
			setCurrentStep(1);
			for (const expert of actors.experts) burst(state, expert);
			for (const expert of actors.experts) {
				state.packets.push({
					from: actors.user,
					to: expert,
					progress: 0,
					speed: 0.022,
					kind: "query",
				});
			}
			state.nodePulse[actors.user] = 0;
			await sleep(STEP_MS);

			// --- Beat 2 — cite ---
			// Label BR fades in. Burst on contributor (the cited person) so
			// the eye is drawn to them; the citation packet flies expert →
			// contributor as confirmation; ~1s later the response packet
			// travels contributor → user, with a burst on user at that moment.
			setCurrentStep(2);
			const lookupExpert =
				actors.experts[Math.floor(Math.random() * actors.experts.length)] ?? actors.user;
			burst(state, actors.contributor);
			state.packets.push({
				from: lookupExpert,
				to: actors.contributor,
				progress: 0,
				speed: 0.022,
				kind: "query",
			});
			window.setTimeout(() => {
				if (!stateRef.current || cancelled) return;
				burst(stateRef.current, actors.user);
				stateRef.current.packets.push({
					from: actors.contributor,
					to: actors.user,
					progress: 0,
					speed: 0.02,
					kind: "answer",
				});
			}, 1100);
			await sleep(STEP_MS);

			// --- Beat 3 — settle ---
			// Label BL fades in. Burst on BOTH contributor and host (they're
			// the recipients of the payment); settle packets follow.
			setCurrentStep(3);
			burst(state, actors.contributor);
			burst(state, actors.host);
			state.packets.push({
				from: actors.user,
				to: actors.contributor,
				progress: 0,
				speed: 0.014,
				kind: "settle",
			});
			state.packets.push({
				from: actors.user,
				to: actors.host,
				progress: 0,
				speed: 0.014,
				kind: "settle",
			});
			await sleep(STEP_MS);

			// Clear story state, brief gap, loop.
			setCurrentStory(null);
			setCurrentStep(-1);
			state.actors = null;
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
				className="block h-full w-full text-fg min-h-[320px]"
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
			return {
				slot: "tl",
				text: `${story.user} ${story.question}`,
			};
		case 1:
			return {
				slot: "tr",
				text: `Routing to ${story.domain}`,
			};
		case 2:
			return {
				slot: "br",
				text: `Pulling ${story.cited}`,
			};
		case 3:
			return {
				slot: "bl",
				text: `Paying ${story.contributor} and the node host`,
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
				"absolute max-w-[18rem] border border-border-strong bg-bg/95 px-3 py-2 text-sm font-medium leading-snug text-fg backdrop-blur shadow-sm sm:text-base",
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
