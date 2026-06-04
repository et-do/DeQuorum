/**
 * Roles state + persistence.
 *
 * For now the user's selected roles live in localStorage. When Firebase
 * Auth lands, this hook will become a thin wrapper around a server-side
 * profile; everything that imports `useRoles` keeps working unchanged.
 */

import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";

export type Role = "user" | "contributor" | "reviewer" | "host";

export const ALL_ROLES: { id: Role; label: string; blurb: string }[] = [
	{
		id: "user",
		label: "Ask questions",
		blurb: "Use the network to query the panel of experts.",
	},
	{
		id: "contributor",
		label: "Publish knowledge",
		blurb: "Submit signed claims and earn when they're cited.",
	},
	{
		id: "reviewer",
		label: "Vote on submissions",
		blurb: "Review pending claims and decide what enters the canon.",
	},
	{
		id: "host",
		label: "Host a node",
		blurb: "Run inference on your GPU and earn per token served.",
	},
];

const STORAGE_KEY = "dequorum.roles";

interface RolesContextValue {
	roles: Set<Role>;
	hasRole: (role: Role) => boolean;
	set: (roles: Iterable<Role>) => void;
	add: (role: Role) => void;
	remove: (role: Role) => void;
	clear: () => void;
	ready: boolean;
}

const RolesContext = createContext<RolesContextValue | null>(null);

function readStoredRoles(): Set<Role> {
	if (typeof window === "undefined") return new Set();
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		if (!raw) return new Set();
		const parsed = JSON.parse(raw);
		if (!Array.isArray(parsed)) return new Set();
		const valid: Role[] = ["user", "contributor", "reviewer", "host"];
		return new Set(parsed.filter((r): r is Role => valid.includes(r)));
	} catch {
		return new Set();
	}
}

export function RolesProvider({ children }: { children: ReactNode }) {
	const [roles, setRoles] = useState<Set<Role>>(() => new Set());
	const [ready, setReady] = useState(false);

	// Read from storage on mount; defer ready=true so SSR/hydration mismatch
	// doesn't briefly flash the "no roles" branch.
	useEffect(() => {
		setRoles(readStoredRoles());
		setReady(true);
	}, []);

	useEffect(() => {
		if (!ready) return;
		window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...roles]));
	}, [roles, ready]);

	const set = useCallback((next: Iterable<Role>) => {
		setRoles(new Set(next));
	}, []);

	const add = useCallback((role: Role) => {
		setRoles((prev) => {
			if (prev.has(role)) return prev;
			const next = new Set(prev);
			next.add(role);
			return next;
		});
	}, []);

	const remove = useCallback((role: Role) => {
		setRoles((prev) => {
			if (!prev.has(role)) return prev;
			const next = new Set(prev);
			next.delete(role);
			return next;
		});
	}, []);

	const clear = useCallback(() => setRoles(new Set()), []);

	const hasRole = useCallback((r: Role) => roles.has(r), [roles]);

	return (
		<RolesContext.Provider value={{ roles, hasRole, set, add, remove, clear, ready }}>
			{children}
		</RolesContext.Provider>
	);
}

export function useRoles(): RolesContextValue {
	const ctx = useContext(RolesContext);
	if (!ctx) throw new Error("useRoles must be used inside <RolesProvider>");
	return ctx;
}
