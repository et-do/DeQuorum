import { useEffect, useState } from "react";

interface HealthResult {
	status: "ok" | "error";
	detail?: string;
}

export default function App() {
	const [health, setHealth] = useState<HealthResult | null>(null);

	useEffect(() => {
		fetch("/api/healthz")
			.then((r) => (r.ok ? r.text() : Promise.reject(r.statusText)))
			.then((text) =>
				setHealth({ status: text === "ok" ? "ok" : "error", detail: text }),
			)
			.catch((err) => setHealth({ status: "error", detail: String(err) }));
	}, []);

	return (
		<div className="min-h-screen flex flex-col">
			<header className="bg-slate-900 text-slate-100">
				<div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
					<h1 className="font-semibold text-lg">dequorum</h1>
					<div className="text-xs text-slate-300">
						{health === null ? (
							<span>checking backend…</span>
						) : health.status === "ok" ? (
							<span className="text-green-400">backend ✓</span>
						) : (
							<span className="text-red-400">backend ✗ — {health.detail}</span>
						)}
					</div>
				</div>
			</header>

			<main className="flex-1 max-w-5xl mx-auto px-4 py-8 w-full">
				<h2 className="text-2xl font-semibold text-slate-900">
					Welcome to DeQuorum
				</h2>
				<p className="mt-2 text-slate-600 max-w-2xl">
					The crowdsourced AI network where every answer is signed by the
					contributors whose knowledge shaped it. This is the v0.1 frontend stub
					— the real query UI, signup flow, and review queue land in upcoming
					phases.
				</p>

				<div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
					<a
						href="/api/query"
						className="bg-white border border-slate-200 rounded-lg p-4 hover:border-indigo-400"
					>
						<div className="font-semibold text-slate-900">Query (Jinja UI)</div>
						<p className="text-sm text-slate-600 mt-1">
							Ask the network a question via the server-rendered interface.
						</p>
					</a>
					<a
						href="/api/review"
						className="bg-white border border-slate-200 rounded-lg p-4 hover:border-indigo-400"
					>
						<div className="font-semibold text-slate-900">Review queue</div>
						<p className="text-sm text-slate-600 mt-1">
							Vote on pending contributions.
						</p>
					</a>
					<a
						href="/api/onboarding"
						className="bg-white border border-slate-200 rounded-lg p-4 hover:border-indigo-400"
					>
						<div className="font-semibold text-slate-900">Sign up</div>
						<p className="text-sm text-slate-600 mt-1">
							Sign the agreement and start contributing.
						</p>
					</a>
				</div>
			</main>

			<footer className="text-xs text-slate-400 text-center py-4">
				Apache-2.0 · v0.1 frontend stub
			</footer>
		</div>
	);
}
