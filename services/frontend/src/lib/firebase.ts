/**
 * Firebase initialization.
 *
 * In dev we connect the Auth SDK to the local emulator (compose's `auth`
 * service on port 9099). The frontend reaches it through the same Caddy
 * origin so there are no CORS surprises: Caddy proxies `/identitytoolkit`
 * to `auth:9099`, and the SDK is happy talking to `${origin}`.
 *
 * In prod we'd swap to the real Firebase Auth endpoints by setting
 * `VITE_FIREBASE_*` env vars at build time.
 */

import { initializeApp } from "firebase/app";
import { connectAuthEmulator, GoogleAuthProvider, getAuth } from "firebase/auth";

const isLocal =
	typeof window !== "undefined" &&
	(window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");

const config = {
	apiKey: (import.meta.env.VITE_FIREBASE_API_KEY as string | undefined) ?? "emulator-key", // emulator accepts anything
	authDomain: (import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string | undefined) ?? "localhost",
	projectId: (import.meta.env.VITE_FIREBASE_PROJECT_ID as string | undefined) ?? "dequorum-local",
};

export const firebaseApp = initializeApp(config);
export const firebaseAuth = getAuth(firebaseApp);

if (isLocal) {
	// disableWarnings stops the SDK from printing the "you are connected
	// to the emulator" banner on every page load.
	connectAuthEmulator(firebaseAuth, "http://localhost:9099", {
		disableWarnings: true,
	});
}

export const googleProvider = new GoogleAuthProvider();
