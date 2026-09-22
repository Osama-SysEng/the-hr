# Architecture

## المكونات الأساسية
- FastAPI + Async Python
- PostgreSQL + SQLAlchemy + Alembic
- Redis + Celery for background tasks
- JWT + RBAC authentication

## الموديولات
1. **Attendance**: biometric, GPS, face recognition, photo verification
2. **Payroll**: Egyptian tax/insurance calculation, payslips, bank transfers
3. **Recruitment**: AI CV screening (GPT-4o-mini), AI interviews, candidate management
4. **Inventory**: products, stock movements, suppliers, purchase orders
5. **Analytics**: dashboards, KPIs, predictions (turnover, payroll forecast)

## قاعدة البيانات
- PostgreSQL 15
- 20+ tables مع العلاقات الكاملة
- Alembic migrations for schema changes
- Multi-tenant separation
