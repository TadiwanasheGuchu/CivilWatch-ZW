# 04 — API Specification

Base path: `/api/v1`. Interactive OpenAPI docs: `/docs` (disabled in production); schema: `/api/v1/openapi.json`.

## Conventions

- JSON request and response bodies with explicit Pydantic schemas.
- Every response carries `X-Request-ID`. A caller may send its own (8–64 chars of `A-Za-z0-9._-`); anything else is replaced.
- Collections are paginated (cursor or `page`/`page_size`, max 100) — defined with the first collection endpoint.
- Status changes use dedicated action endpoints (e.g. `POST /issues/{id}/transitions`), never a generic PATCH.

### Error envelope

Every error, including 404/405/422/500, uses:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request contains invalid data.",
    "details": [{ "location": ["body", "email"], "message": "...", "type": "..." }],
    "request_id": "4f0c…"
  }
}
```

`code` is a stable machine-readable slug; `message` is safe to show users; 500 responses never include internal details.

## Implemented endpoints

### `GET /api/v1/health/live`
Process liveness. Unauthenticated. `200 {"status": "ok"}`.

### `GET /api/v1/health/ready`
Dependency readiness. Unauthenticated; reveals only coarse status.

```json
{ "status": "ok", "database": "ok", "postgis": "ok", "cache": "ok" }
```

Returns `503` with the same shape and `"status": "degraded"` when any dependency is unavailable.

## Planned endpoint groups

`/auth`, `/users`, `/councils`, `/departments`, `/issues`, `/assignments`, `/map`, `/analytics`, `/notifications` — each documented here when implemented.
