# Dev environment setup checklist

One-time setup for a fresh clone or a devcontainer rebuild. Skim through;
everything below is verified token-free.

## 1. After rebuilding the devcontainer

The slim devcontainer ships:
- Docker CLI + Docker daemon (via `docker-in-docker` feature)
- Git + GitHub CLI
- Python 3.13 (just enough to run pre-commit — language tools live in the service containers)
- `pre-commit` (installed system-wide by `postCreateCommand`)

It does **not** ship: `uv`, `node`, `npm`, `ollama`, language-specific dev tools.
Those live in each service's container.

After the devcontainer finishes building, verify:

```bash
docker --version          # docker CLI present
docker compose version    # compose v2 present
pre-commit --version      # installed via postCreate
git --version
gh --version
```

## 2. Bring up the stack

From the VS Code Command Palette: **Tasks: Run Task → `compose: up (start/restart, rebuild if Dockerfile changed)`**

Or from the terminal:

```bash
docker compose up -d --build
```

Then in another terminal (or another task instance) tail the logs:

**Tasks: Run Task → `compose: logs (follow all services)`**

```bash
docker compose logs -f --tail=200
```

Once everything is healthy, hit http://localhost — Caddy routes `/` to the
Vite dev server and `/api/*` to the FastAPI app.

## 3. First-run notes per service

| Service | First-run cost | What's happening |
| --- | --- | --- |
| `db` | ~5s | Postgres init scripts create the `dequorum` + `dequorum_test` databases |
| `ollama` | 5–10 min | Pulls `qwen2.5-coder:7b` (~5 GB). Persists in the `ollama-models` volume across restarts |
| `app` | ~30s first build, ~5s on subsequent | First build: `uv sync` resolves deps + writes `services/app/uv.lock` back to host via the volume mount (commit it after first build for reproducible CI). On startup the FastAPI lifespan runs `alembic upgrade head` against the `db` service then seeds contributors/contributions/categories if their tables are empty. |
| `frontend` | ~20s | `npm install` resolves and creates `package-lock.json`. **Commit the lockfile after the first compose run** so CI can switch to `npm ci` for faster builds (see §6). |
| `proxy` | <1s | Caddy binary |
| `auth` | ~30s | Firebase CLI downloads via npm |

## 4. Pre-commit — verified token-free

Hooks all install from public GitHub releases / PyPI on first `pre-commit run`.
None require auth tokens or SaaS APIs. See [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml).

| Hook | Hook bin source | Auth |
| --- | --- | --- |
| `ruff` | astral-sh public release | none |
| `biome-check` | biomejs public release | none |
| `hadolint` | AleksaC mirror of hadolint public binary | none |
| `shellcheck` | koalaman public release | none |
| `yamllint` | PyPI | none |
| `typos` | crate-ci public release | none |
| `gitleaks` | gitleaks public release | none |
| `validate-pyproject` | PyPI | none |
| `pre-commit-hooks` | PyPI | none |

`pre-commit install` is already wired in `postCreateCommand`. To run manually:

```bash
pre-commit run --all-files
```

## 5. GitHub Actions — verified token-free, with 3 repo-setting checkboxes

All 6 workflows use only the built-in `GITHUB_TOKEN` (automatic on every run).
No PATs, no `secrets.*` references anywhere.

But GitHub's modern defaults require these one-time toggles in **Settings →** :

| Where in Settings | What to enable | Required by |
| --- | --- | --- |
| **Actions → General → Workflow permissions** | "Read and write permissions" + "Allow GitHub Actions to create and approve pull requests" | `pr-labeler`, `stale` (modifying issues/PRs) |
| **Code security → Code scanning** | "Set up CodeQL → Default" *or* leave on "Advanced" so the workflow file controls config | `codeql.yml` uploads SARIF to the Security tab |
| **Code security → Dependabot** | Enable "Dependency graph", "Dependabot alerts", "Dependabot version updates" | `.github/dependabot.yml` |

That's it. After flipping those, all workflows work without further intervention.

### Workflow-by-workflow audit

| Workflow | Trigger | Permissions | Auth | One-time GitHub setting needed |
| --- | --- | --- | --- | --- |
| `ci-python.yml` | push / PR on `services/app/**` | default read | none | none |
| `ci-frontend.yml` | push / PR on `services/frontend/**` | default read | none | none |
| `docker-build.yml` | push / PR on `services/**` or `compose.yml` | default read | none | none (uses GHA cache backend, also token-free) |
| `codeql.yml` | push / PR / weekly | `security-events: write`, `contents: read` | built-in `GITHUB_TOKEN` | Code scanning enabled (above) |
| `pr-labeler.yml` | PR | `contents: read`, `pull-requests: write` | built-in `GITHUB_TOKEN` | Workflow permissions allow write (above) |
| `stale.yml` | daily 6 UTC | `issues: write`, `pull-requests: write` | built-in `GITHUB_TOKEN` | Workflow permissions allow write (above) |
| `dependabot.yml` (config, not a workflow) | weekly | n/a — runs as GitHub-side service | none | Dependabot enabled (above) |

## 6. First-commit lockfile note

`services/frontend/package-lock.json` doesn't exist yet. The CI workflow
handles this gracefully (`npm install` fallback). After the first
`docker compose up frontend` produces a lockfile inside the container's
volume, copy it to the host and commit it:

```bash
docker compose cp frontend:/app/package-lock.json services/frontend/package-lock.json
git add services/frontend/package-lock.json
git commit -m "chore(frontend): commit initial npm lockfile"
```

Then re-enable CI caching by editing `.github/workflows/ci-frontend.yml`:
- restore `cache: "npm"` + `cache-dependency-path: services/frontend/package-lock.json` in `setup-node`
- replace the conditional install with plain `npm ci`

## 7. Daily workflow

```
# Start everything:
Tasks: Run Task → compose: up (start/restart, rebuild if Dockerfile changed)

# Watch all services:
Tasks: Run Task → compose: logs (follow all services)

# Run the Python tests inside the running app container:
# (tests point at the dequorum_test database, isolated from dev data)
docker compose exec app uv run pytest

# Apply pending Alembic migrations against the dev DB (runs automatically
# on app startup; this is for when you write a new migration mid-session):
docker compose exec app uv run dequorum db upgrade

# Open a shell in any service:
docker compose exec app bash
docker compose exec db psql -U dequorum_app dequorum
docker compose exec db psql -U dequorum_app dequorum_test  # the isolated test DB

# Stop everything:
docker compose down

# Reset everything (drops volumes — Postgres data + Ollama models):
docker compose down -v
```

## 8. What can go wrong on first rebuild

| Symptom | Cause | Fix |
| --- | --- | --- |
| `docker: command not found` after rebuild | docker-in-docker feature didn't install | Rebuild the devcontainer ("Dev Containers: Rebuild Container") |
| `sudo: python3: command not found` during postCreate | sudo's `secure_path` doesn't include the python feature's install dir | The current devcontainer.json runs the pip step without sudo (installing to `~/.local/bin`). If you see this on an older devcontainer.json, rebuild after pulling — or rerun the install manually: `python3 -m pip install --user --break-system-packages pre-commit && ~/.local/bin/pre-commit install` |
| `pre-commit: command not found` | postCreate finished but `~/.local/bin` isn't on PATH | The devcontainer's `remoteEnv` prepends it; if your shell session predates the rebuild, open a new terminal |
| Ollama model never finishes pulling | Slow network or paused download | `docker compose logs -f ollama` — restart with `docker compose restart ollama` |
| App container restart loops | Wrong env var, missing dep | `docker compose logs -f app` — usually says exactly what's wrong |
| Port already in use | Something else on the host is on 80/8000/5432/etc. | Stop the host process or edit `compose.yml` host-port mapping |
| Pre-commit hook fails to download | Behind a corp proxy | Set `HTTPS_PROXY` env in devcontainer.json |
