# LOGGING — The H.R (`the-hr`)

Central module: `app/core/logging_utils.py` (stdlib only, no new dependencies).
Import: `from app.core.logging_utils import get_logger, request_id_ctx, new_request_id`.

## Schema (one JSON line per record)

`timestamp` (UTC ISO-8601 ms) · `level` · `service` (`the-hr`) · `env` ·
`version` (GIT_SHA) · `request_id` · `event` · `message`, plus optional
`error.stack` on exceptions and redacted `extra={"fields": {...}}` keys.

## Levels

`LOG_LEVEL` env (default: `debug` outside production, `info` in production).
Use `debug` (diagnostics) · `info` (access + business events) ·
`warning` (degraded, e.g. missing optional lib) · `error/exception` (failures).

## Env vars

| Var | Example (safe) | Purpose |
|---|---|---|
| `SERVICE_NAME` | `the-hr` | service tag in every line |
| `LOG_LEVEL` | `INFO` | minimum level |
| `GIT_SHA` | `dev` | version tag |
| `ENVIRONMENT` | `development` | env tag |

## Redaction

Keys containing any of these are replaced with `***` in `fields`:
`password, passwd, token, secret, apikey, api_key, authorization, cookie,
set-cookie, cvv, card_number, national_id, passport`.
Never log secrets, raw phone numbers, emails, or national IDs in messages —
log opaque tags instead (see `face_recognition_service._tag`).

## Request ID

Middleware (`request_id_middleware` in `app/main.py`) reads `X-Request-ID`
or generates one (`uuid4` hex 16), binds it to `request_id_ctx`, echoes it
back as `X-Request-ID`, and emits one access line:
`method / route / status / duration_ms` (`event: http.access`).

Search by request: `grep '"request_id": "<id>"' app.log`
(or `jq 'select(.request_id=="<id>")'`).
