# services/frontend

The full user-facing surface of DeQuorum. No HTML is served by any other
service — `services/app` is a JSON API only.

## Routes

| Path | Purpose |
| --- | --- |
| `/` | Marketing landing (Bittensor-style hero, Launch App CTA) |
| `/about` | Mission + principles |
| `/docs` | "How it works" walkthrough |
| `/pricing` | Marketplace economics (linked from `cost-model.md`) |
| `/app` | Dashboard with network counts + quick links |
| `/app/query` | Ask the network; renders proof chain + ledger |
| `/app/review` | Pending queue; real-time updates via SSE; vote inline |
| `/app/contributions` | List with search + status/expert filters |
| `/app/contributions/$id` | Detail + lineage link + vote history |
| `/app/experts` | Seed expert registry |
| `/app/contributors` | Signed-up contributors |
| `/app/contributors/$id` | Contributor profile + their contributions |
| `/app/categories` | Curated taxonomy |
| `/app/lineages/$id` | Version history for a lineage |
| `/app/onboarding` | Signup form + agreement preview + keypair generation |

## Stack

| Concern | Choice |
| --- | --- |
| Build / dev server | Vite 6 |
| Framework | React 19 |
| Routing | TanStack Router 1 (file-based, `target: "react"`) |
| Data fetching | TanStack Query 5 |
| Types | TypeScript 5 |
| Styling | Tailwind 4 (CSS-first config + `@tailwindcss/vite`) |
| Font | IBM Plex Mono (self-hosted via `@fontsource/ibm-plex-mono`) |
| Theme | CSS variables + `data-theme` attribute; no-flash init in `index.html` |
| Tests | Vitest + Testing Library + jsdom |
| Lint / format | Biome (tabs, double quotes) |

## Layout

```
src/
├── main.tsx                          # bootstrap: QueryClient + Router + Theme
├── routeTree.gen.ts                  # auto-generated, gitignored
├── components/
│   ├── layout/ {Footer, TopNav}      # site chrome
│   └── ui/    {Button, Container, Link, ThemeToggle}
├── lib/
│   ├── api/ {client, types, index}   # typed fetch wrappers for /api/v1/*
│   ├── theme.tsx                     # ThemeProvider + useTheme
│   ├── useReviewStream.ts            # SSE consumer for /api/v1/review/stream
│   ├── cn.ts                         # clsx + twMerge
│   └── env.ts                        # APP_PATH, SITE_NAME, NAV_LINKS
├── routes/
│   ├── __root.tsx                    # root layout (TopNav + Outlet + Footer)
│   ├── {index,about,docs,pricing}.tsx
│   ├── app.tsx                       # /app/* layout (sub-nav + Outlet)
│   ├── app.index.tsx                 # /app
│   ├── app.query.tsx
│   ├── app.review.tsx
│   ├── app.contributions.{index,$id}.tsx
│   ├── app.contributors.{index,$id}.tsx
│   ├── app.experts.tsx
│   ├── app.categories.tsx
│   ├── app.lineages.$id.tsx
│   └── app.onboarding.tsx
└── styles/ {index, tokens}.css       # tailwind import + CSS vars
```

## Run

Inside compose:

```bash
docker compose up frontend
# → http://localhost (Caddy)
# → http://localhost:5173 (direct Vite)
```

Standalone:

```bash
cd services/frontend
npm install
npm run dev
```

The dev server proxies `/api/*` to the app service (Caddy in compose, raw
`localhost:8000` outside, configurable via `VITE_PROXY_API_TARGET`).

## Adding a dependency

Because the container's `node_modules` is an anonymous volume:

```bash
# Edit package.json on host
docker compose exec frontend npm install
git add services/frontend/package.json services/frontend/package-lock.json
git commit -m "chore(frontend): add <package>"
```

No rebuild required — `npm install` inside the container updates
`node_modules` (anonymous volume) and the lockfile (bind-mounted to host).

## Tests

```bash
docker compose exec frontend npm run test:run
```

Production target: **Firebase Hosting**. The `prod` Dockerfile stage
exists for parity testing only.
