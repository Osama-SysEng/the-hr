# SCALING — The-HR Backend

- Bottleneck: DB connection churn + unbounded list endpoints (inventory) + single uvicorn worker by default.
- Tuning: `UVICORN_WORKERS` (default 2); pool `pool_size=20/max_overflow=10/pool_recycle=3600/pool_pre_ping=True` in `backend/app/core/database.py`; `RATE_LIMIT_PER_MINUTE` (default 600, sliding window per IP+path, `/health` exempt); list endpoints capped `limit=50` default, `500` max.
- Known limits: rate limiter is in-memory per process (limits don't aggregate across workers — use Redis for strict global limits); recommended tenant indexes live in `backend/app/configs/database_tuning.py::RECOMMENDED_INDEXES` and `001_initial_schema` — verify on large tenants with `EXPLAIN ANALYZE`; report-summary item breakdown is a bounded page (aggregates are full-set).
