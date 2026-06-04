/**
 * Local account state for the currently-signed-up contributor.
 *
 * Stored fields: contributor_id, display_name, public_key_hex.
 * Private key is NOT stored — the onboarding flow shows it once and
 * leaves it up to the user to record it. When Firebase Auth + key
 * management land, this becomes a server-side profile + WebCrypto.
 */

import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";

export interface LocalAccount {
	contributor_id: string;
	display_name: string;
	public_key_hex: string;
}

const STORAGE_KEY = "dequorum.account";

interface AccountContextValue {
	account: LocalAccount | null;
	setAccount: (next: LocalAccount | null) => void;
	clear: () => void;
	ready: boolean;
}

const AccountContext = createContext<AccountContextValue | null>(null);

function read(): LocalAccount | null {
	if (typeof window === "undefined") return null;
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw);
		if (
			parsed &&
			typeof parsed.contributor_id === "string" &&
			typeof parsed.display_name === "string" &&
			typeof parsed.public_key_hex === "string"
		) {
			return parsed as LocalAccount;
		}
	} catch {
		// fall through
	}
	return null;
}

export function AccountProvider({ children }: { children: ReactNode }) {
	const [account, setAccountState] = useState<LocalAccount | null>(null);
	const [ready, setReady] = useState(false);

	useEffect(() => {
		setAccountState(read());
		setReady(true);
	}, []);

	useEffect(() => {
		if (!ready) return;
		if (account) {
			window.localStorage.setItem(STORAGE_KEY, JSON.stringify(account));
		} else {
			window.localStorage.removeItem(STORAGE_KEY);
		}
	}, [account, ready]);

	const setAccount = useCallback((next: LocalAccount | null) => {
		setAccountState(next);
	}, []);

	const clear = useCallback(() => setAccountState(null), []);

	return (
		<AccountContext.Provider value={{ account, setAccount, clear, ready }}>
			{children}
		</AccountContext.Provider>
	);
}

export function useAccount(): AccountContextValue {
	const ctx = useContext(AccountContext);
	if (!ctx) throw new Error("useAccount must be used inside <AccountProvider>");
	return ctx;
}
