# services/db

Postgres 16 for local DeQuorum development. The same schema (once ported from
SQLite) targets Google Cloud SQL Postgres in production.

## Status

- ✅ Container builds, accepts connections on `:5432`
- ✅ Bootstrap creates `dequorum` + `dequorum_test` databases on first start
- ⏳ App still uses SQLite at runtime. Porting the stores to Postgres is its
  own focused phase (data model is documented in
  [`docs/architecture/data-model.dbml`](../../docs/architecture/data-model.dbml)).

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

Tree planned at `services/db/migrations/` (alembic). Not yet present. When it
lands, the compose entrypoint will run `alembic upgrade head` against the
`dequorum` database before the app starts.
