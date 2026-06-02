# services/proxy

Caddy reverse proxy. Local-only — production uses Firebase Hosting + Cloud
Run managed TLS, no separate proxy needed.

## Routes

| Pattern | Forwards to |
| --- | --- |
| `/api/*` | `app:8000` (strips the `/api` prefix) |
| `/healthz` | inline `ok` response (for compose healthcheck) |
| `/*` | `frontend:5173` (Vite dev server with HMR) |

## Bind

Exposed on `localhost:80` by [compose.yml](../../compose.yml). Open
http://localhost in your browser to hit the full stack.

## Production parity

In production, `/api/*` maps to a Cloud Run URL and `/*` is served by
Firebase Hosting. The same URL shape works locally because Caddy emulates
that routing — no `/api` prefix in app code, no environment-specific URLs in
the frontend.
