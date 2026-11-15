# syntax=docker/dockerfile:1
# Two targets:
#   runtime (default) — production: locked runtime dependencies only, no tests.
#   dev               — local development and CI: adds test tools and the tests.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY requirements.lock ./
RUN pip install -r requirements.lock

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY alembic ./alembic
RUN pip install --no-deps .

FROM base AS dev
RUN pip install ".[dev]"
COPY tests ./tests
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS runtime
USER app
EXPOSE 8000
# Behind a reverse proxy, set FORWARDED_ALLOW_IPS to the proxy's address so
# rate limits see real client IPs (docs/09-deployment-guide.md).
ENV FORWARDED_ALLOW_IPS=127.0.0.1
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips \"$FORWARDED_ALLOW_IPS\" --workers ${WEB_CONCURRENCY:-2}"]
