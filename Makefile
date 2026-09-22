.PHONY: install dev test lint security migrate seed backup cleanup health

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

dev:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest backend/app/tests -v --tb=short

lint:
	ruff check backend/app/

security:
	bandit -r backend/app/ -f json -o bandit.json
	pip-audit --format=json || true

migrate:
	cd backend && alembic upgrade head

seed:
	python scripts/seed_db.py

backup:
	python scripts/backup_db.py

cleanup:
	python scripts/cleanup.py

health:
	python scripts/health_check.py
