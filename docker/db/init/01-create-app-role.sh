#!/bin/sh
# Runs once, when the database volume is first initialised.
# Creates the unprivileged role the API connects as. It owns no tables, so
# PostgreSQL Row-Level Security applies to it; migrations grant its privileges.
set -eu

: "${APP_DB_PASSWORD:?Set APP_DB_PASSWORD in .env}"

# The password is passed as a psql variable and quoted by psql (:'name'),
# never interpolated into SQL by the shell.
echo "CREATE ROLE civicwatch_app LOGIN PASSWORD :'app_password';" | psql \
  -v ON_ERROR_STOP=1 \
  -v app_password="$APP_DB_PASSWORD" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB"
