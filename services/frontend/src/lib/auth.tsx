/**
 * Firebase Auth wrapper.
 *
 * `AuthProvider` subscribes to `onAuthStateChanged` and exposes the
 * current user + a fetched ID token. Every API call goes through
 * `withAuthHeader`, which lazily refreshes the token (Firebase caches
 * for ~55 min; one extra getIdToken call is cheap and avoids 401s when
 * the in-memory token has just expired).
 *
 * Sign-in helpers cover the two flows our onboarding wizard offers:
 * email/password and Google. Both work against the local emulator.
 */

import {
	createUserWithEmailAndPassword,
	type User as FirebaseUser,
	signOut as fbSignOut,
	onAuthStateChanged,
	signInWithEmailAndPassword,
	signInWithPopup,
} from "firebase/auth";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { firebaseAuth, googleProvider } from "./firebase";

interface AuthState {
	user: FirebaseUser | null;
	ready: boolean;
	signInEmail: (email: string, password: string) => Promise<void>;
	signUpEmail: (email: string, password: string, displayName?: string) => Promise<void>;
	signInGoogle: () => Promise<void>;
	signOut: () => Promise<void>;
	getIdToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<FirebaseUser | null>(null);
	const [ready, setReady] = useState(false);

	useEffect(() => {
		const unsub = onAuthStateChanged(firebaseAuth, (u) => {
			setUser(u);
			setReady(true);
		});
		return unsub;
	}, []);

	const signInEmail = useCallback(async (email: string, password: string) => {
		await signInWithEmailAndPassword(firebaseAuth, email, password);
	}, []);

	const signUpEmail = useCallback(async (email: string, password: string, displayName?: string) => {
		const cred = await createUserWithEmailAndPassword(firebaseAuth, email, password);
		if (displayName) {
			const { updateProfile } = await import("firebase/auth");
			await updateProfile(cred.user, { displayName });
		}
	}, []);

	const signInGoogle = useCallback(async () => {
		await signInWithPopup(firebaseAuth, googleProvider);
	}, []);

	const signOut = useCallback(async () => {
		await fbSignOut(firebaseAuth);
	}, []);

	const getIdToken = useCallback(async () => {
		const u = firebaseAuth.currentUser;
		if (!u) return null;
		return u.getIdToken(false);
	}, []);

	return (
		<AuthContext.Provider
			value={{
				user,
				ready,
				signInEmail,
				signUpEmail,
				signInGoogle,
				signOut,
				getIdToken,
			}}
		>
			{children}
		</AuthContext.Provider>
	);
}

export function useAuth(): AuthState {
	const ctx = useContext(AuthContext);
	if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
	return ctx;
}

/**
 * Resolve an Authorization header for the current user. Returns an
 * empty object if no user is signed in — callers can spread it without
 * a conditional.
 */
export async function withAuthHeader(): Promise<Record<string, string>> {
	const u = firebaseAuth.currentUser;
	if (!u) return {};
	const token = await u.getIdToken(false);
	return { Authorization: `Bearer ${token}` };
}
