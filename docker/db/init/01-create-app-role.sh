#!/bin/sh
# Runs once, when the database volume is first initialised.
# Creates the unprivileged roles the API and the background worker connect as.
# They own no tables, so PostgreSQL Row-Level Security applies to them;
# migrations grant their privileges.
set -eu

: "${APP_DB_PASSWORD:?Set APP_DB_PASSWORD in .env}"
: "${WORKER_DB_PASSWORD:?Set WORKER_DB_PASSWORD in .env}"

# The password is passed as a psql variable and quoted by psql (:'name'),
# never interpolated into SQL by the shell.
psql \
  -v ON_ERROR_STOP=1 \
  -v app_password="$APP_DB_PASSWORD" \
  -v worker_password="$WORKER_DB_PASSWORD" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<'SQL'
CREATE ROLE civicwatch_app LOGIN PASSWORD :'app_password';
CREATE ROLE civicwatch_worker LOGIN PASSWORD :'worker_password';
SQL
