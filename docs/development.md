# Development

## المتطلبات
- Python 3.11+
- Node.js 20+
- PostgreSQL 15
- Redis 7
- Docker (اختياري)

## الإعداد
```bash
pip install -r backend/requirements.txt
cd frontend && npm install
```

## التشغيل
```bash
# Backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm run dev
```

## الاختبارات
```bash
pytest backend/app/tests -v
```

## قاعدة البيانات
```bash
alembic upgrade head
alembic downgrade -1
```

## الـ Lint
```bash
ruff check backend/app/
```

## الأمان
```bash
bandit -r backend/app/ -f json -o bandit.json
pip-audit --format=json
```
