# services/frontend

Vite + React + Tailwind v4 SPA. **Status:** v0.1 stub. Real query UI, signup
flow, and review queue land in subsequent phases. The
[server-rendered Jinja UI](../app/src/dequorum/web/templates/) in the app
service is the current user-facing surface.

Production target: **Firebase Hosting**. The `prod` Dockerfile stage is for
parity testing only.

## Run

Inside compose: `docker compose up frontend` → http://localhost:5173

Standalone:
```bash
cd services/frontend
npm install
npm run dev
```

The dev server proxies `/api/*` to the app service (Caddy in compose; raw
localhost:8000 outside compose, configurable via `VITE_PROXY_API_TARGET`).

## Tech stack

| Concern | Choice |
| --- | --- |
| Build / dev server | Vite 6 |
| Framework | React 19 |
| Types | TypeScript 5 |
| Styling | Tailwind 4 |
| Auth (future) | Firebase Auth |
| Routing (future) | TBD (react-router or @tanstack/router) |

## Future phases

- Replace the dashboard tiles with a real query interface
- Add Firebase Auth integration against `services/auth-emulator`
- Implement client-side keypair generation + agreement signing
- Build the contributor profile, review queue, and lineage views
