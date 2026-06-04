# Multi-stage build for the DeQuorum orchestrator service.
#
# Targets:
#   - dev:  uv + source mounted for hot reload (used by compose dev override)
#   - prod: built wheel, no source tree, slim runtime (Cloud Run target)

# --- shared base ---------------------------------------------------------
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/root/.local/bin:${PATH}"

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/* \
 && curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app


# --- dev: source-mounted hot-reload target -------------------------------
FROM base AS dev

# Install dependencies (no source copy — that's mounted at runtime by compose).
# `--frozen` is omitted here so uv re-locks if pyproject.toml drifted from
# uv.lock. The lockfile is bind-mounted from the host in compose, so any
# re-lock propagates back automatically.
#
# The uv cache mount keeps downloaded wheels across builds. Without it,
# every rebuild re-downloads ~2 GB of torch/transformers/chromadb wheels.
# With it, only changed deps re-download.
COPY pyproject.toml README.md ./
COPY uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --extra dev --no-install-project

# When source is mounted, install the package in editable mode at start.
# The sync here is fast (just installs the editable project itself); the
# heavy deps were already installed at build time and live in /app/.venv.
CMD ["sh", "-c", "uv sync --extra dev --inexact && exec uv run uvicorn dequorum.web.app:create_app --factory --host 0.0.0.0 --port 8000 --reload"]


# --- prod: built wheel, slim runtime -------------------------------------
FROM base AS builder

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev


FROM python:3.13-slim AS prod

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# Copy the built virtualenv + source from the builder stage.
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Cloud Run sets PORT; honor it. Default 8000 for local compose.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn dequorum.web.app:create_app --factory --host 0.0.0.0 --port ${PORT}"]
