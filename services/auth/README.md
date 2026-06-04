# services/auth

Firebase Auth — same service in dev and prod, different backends.

- **Locally**: this container runs the Firebase Auth Emulator (the app talks
  to it via `FIREBASE_AUTH_EMULATOR_HOST=auth:9099`).
- **Production**: Firebase Auth itself, hosted by Google. The app speaks the
  same REST API; unsetting `FIREBASE_AUTH_EMULATOR_HOST` switches it over.

## Ports

| Port | What |
| --- | --- |
| 9099 | Auth REST API |
| 4000 | Emulator UI (browse users, test sign-in flows) |

## Connect from the app

Already wired in `compose.yml`:

```
FIREBASE_AUTH_EMULATOR_HOST=auth:9099
```

Any Firebase Admin SDK call from the app transparently uses the emulator
instead of the real Firebase backend. Unsetting this variable in production
makes the same code talk to real Firebase.

## Connect from the frontend

```ts
import { connectAuthEmulator, getAuth } from "firebase/auth";

const auth = getAuth();
if (import.meta.env.DEV) {
  connectAuthEmulator(auth, "http://localhost:9099");
}
```

## What lives in this service

- User accounts (created via sign-up flow or seeded by tests)
- Sign-in providers (email/password, anonymous, OIDC custom)
- Custom claims (used to bind a Firebase uid to a DeQuorum `contributor_id`)

The DeQuorum contributor record (signing keypair + tier + agreement signature)
is stored separately in the app's database. The Firebase uid is the identity
primitive that the app uses to look up the contributor.
