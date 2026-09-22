# Deployment

## Docker Compose
```bash
cd the-hr
docker-compose up -d
```

## Puter Cloud
```bash
# Deploy backend
puter deploy --config puter.config.json

# Or manually
# Upload backend/ folder to Puter cloud
```

## التهيئة
.env.example:
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
```

## Commands
- migrate: `alembic upgrade head`
- rollback: `alembic downgrade -1`
- seed: `python scripts/seed_db.py`
- backup: `python scripts/backup_db.py`
- cleanup: `python scripts/cleanup.py`
- health: `python scripts/health_check.py`
