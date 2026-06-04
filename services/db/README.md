# services/db

Postgres 16 for local DeQuorum development. The same schema targets Google
Cloud SQL Postgres in production.

## Status

- ✅ Container builds, accepts connections on `:5432`
- ✅ Bootstrap creates `dequorum` + `dequorum_test` databases on first start
- ✅ App connects via psycopg3; schema applied by Alembic on app startup

## Connect

From inside the compose network:

```
postgresql://dequorum_app:dev-only-not-for-prod@db:5432/dequorum
```

From the host (compose exposes `:5432`):

```
postgresql://dequorum_app:dev-only-not-for-prod@localhost:5432/dequorum
```

## Migrations

Alembic migrations live in
[`services/app/src/dequorum/db/migrations/`](../app/src/dequorum/db/migrations/).
The FastAPI app lifespan runs `alembic upgrade head` on startup, so a fresh
database is ready to use without any manual step. To run migrations
explicitly:

```bash
docker compose exec app uv run dequorum db upgrade
```
