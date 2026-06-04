-- DeQuorum Postgres bootstrap.
--
-- This script runs only on first container start (when the data dir is empty).
-- To re-run after editing, `docker compose down -v` to drop the db-data
-- volume and bring the service back up.
--
-- The actual schema (contributions, votes, contributors, agreements,
-- categories, lineages) is currently embedded in the Python store modules
-- and uses SQLite. The Postgres-port of that schema lands in a future phase
-- via an alembic migration tree under services/db/migrations/.

-- Role must exist before we set it as the database OWNER below.
CREATE ROLE dequorum_app WITH LOGIN PASSWORD 'dev-only-not-for-prod';

-- Owning the database is the cleanest way to grant CREATE on the `public`
-- schema. As of Postgres 15, `GRANT ALL ON DATABASE` no longer implies
-- schema-level CREATE — only the database owner can create objects in
-- public unless that's granted explicitly. Owning the db side-steps the
-- whole grant dance.
CREATE DATABASE dequorum      OWNER dequorum_app;
CREATE DATABASE dequorum_test OWNER dequorum_app;
