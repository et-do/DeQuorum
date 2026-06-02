# Postgres for local DeQuorum development.
#
# Production target: Google Cloud SQL Postgres 16 (same major version, no
# server-side code lives in this image — schema is applied at startup via
# the init scripts, so the same SQL works locally and in Cloud SQL).

FROM postgres:16-alpine

# init/ runs only the first time the data directory is empty. Idempotent
# bootstrap of the dequorum + dev databases lives here.
COPY init/ /docker-entrypoint-initdb.d/
