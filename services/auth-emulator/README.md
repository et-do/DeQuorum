# services/auth-emulator

Firebase Auth Emulator for local-only development. In production this entire
service is replaced by real Firebase Auth — the app talks to either through
the same REST API, so swap is a config change (`FIREBASE_AUTH_EMULATOR_HOST`
env var unset → real Firebase).

## Ports

| Port | What |
| --- | --- |
| 9099 | Auth emulator REST API |
| 4000 | Emulator UI (browse users, test sign-in flows) |

## Connect from the app

Set in `compose.yml` for the app service:

```
FIREBASE_AUTH_EMULATOR_HOST=auth-emulator:9099
```

Any Firebase Admin SDK call from the app then transparently uses the emulator
instead of the real Firebase backend.

## Connect from the frontend

```ts
import { connectAuthEmulator, getAuth } from "firebase/auth";

const auth = getAuth();
if (import.meta.env.DEV) {
  connectAuthEmulator(auth, "http://localhost:9099");
}
```

## What lives in the emulator

- User accounts (created via sign-up flow or seeded by tests)
- Sign-in providers (email/password, anonymous, OIDC custom)
- Custom claims (used to bind a Firebase uid to a DeQuorum `contributor_id`)

The DeQuorum contributor record (signing keypair + tier + agreement signature)
is stored separately in the app's database. The Firebase uid is just the
identity primitive that the app uses to look up the contributor.
