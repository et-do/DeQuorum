# Multi-stage build for the DeQuorum SPA.
#
# Targets:
#   - dev:  Vite dev server with HMR (used by compose dev override)
#   - prod: static build, served by anything (Firebase Hosting target)

FROM node:26-alpine AS base

# Not /app — that collides with the SPA's /app URL route. Vite resolves
# URLs against the working directory, so `GET /app` would try to read the
# `/app` directory and EISDIR. /workspace is neutral.
WORKDIR /workspace

# Prefer `npm ci` for reproducibility when a lockfile is present — it
# errors if the lock drifts from package.json instead of silently
# rewriting it. Falls back to `npm install` only on the very first build
# (no lockfile committed yet); the install writes one, which the bind
# mount surfaces back to the host for you to commit.
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then \
        npm ci --no-audit --no-fund; \
    else \
        npm install --no-audit --no-fund; \
    fi


# --- dev: Vite HMR server ---
FROM base AS dev
ENV NODE_ENV=development
EXPOSE 5173
CMD ["npm", "run", "dev"]


# --- builder: produce the static bundle ---
FROM base AS builder
COPY . .
RUN npm run build


# --- prod: serve the static bundle ---
# In production this is replaced by Firebase Hosting; this stage exists so
# `docker compose --profile prod up frontend` works for parity testing.
FROM nginx:alpine AS prod
COPY --from=builder /workspace/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
