# Multi-stage build for the DeQuorum SPA.
#
# Targets:
#   - dev:  Vite dev server with HMR (used by compose dev override)
#   - prod: static build, served by anything (Firebase Hosting target)

FROM node:22-alpine AS base
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund


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
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
