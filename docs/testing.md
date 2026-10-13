# Testing

## تشغيل الاختبارات
```bash
pytest backend/app/tests -v --tb=short
```

## الأنواع
- Unit tests: اختبار الدوال والخدمات كل على حدة
- Integration tests: اختبار الـ API endpoints مع قاعدة البيانات
- Security tests: bandit, pip-audit, safety

## الـ CI
GitHub Actions يعمل:
- Lint (ruff)
- Tests (pytest)
- Security scan (bandit, pip-audit)
