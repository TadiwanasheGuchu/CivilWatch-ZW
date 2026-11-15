#!/bin/sh
# Production entry point for the API container.
#
# Hosts with a release step (deploy/compose.prod.yml runs `migrate`) leave the
# flags off. Free hosts without one (Render's free plan) set
#   CIVICWATCH_PREPARE_DATABASE_ON_START=true  roles + migrations before serving
#   CIVICWATCH_SEED_DEMO_ON_START=true         labelled sample data, once
set -eu

if [ "${CIVICWATCH_PREPARE_DATABASE_ON_START:-false}" = "true" ]; then
  python -m app.cli prepare-database
fi

if [ "${CIVICWATCH_SEED_DEMO_ON_START:-false}" = "true" ]; then
  python -m app.cli seed-demo --confirm --if-empty --password-from-env
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
