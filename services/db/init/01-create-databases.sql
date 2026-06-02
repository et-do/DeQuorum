-- DeQuorum Postgres bootstrap.
--
-- This script runs only on first container start (when the data dir is empty).
-- Idempotent: safe to re-run by removing the volume and bringing the service
-- back up.
--
-- The actual schema (contributions, votes, contributors, agreements,
-- categories, lineages) is currently embedded in the Python store modules
-- and uses SQLite. The Postgres-port of that schema lands in a future phase
-- via an alembic migration tree under services/db/migrations/.

CREATE DATABASE dequorum;
CREATE DATABASE dequorum_test;

-- Roles
CREATE ROLE dequorum_app WITH LOGIN PASSWORD 'dev-only-not-for-prod';
GRANT ALL PRIVILEGES ON DATABASE dequorum      TO dequorum_app;
GRANT ALL PRIVILEGES ON DATABASE dequorum_test TO dequorum_app;
