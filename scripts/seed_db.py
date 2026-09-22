#!/usr/bin/env python
"""The H.R - Seed Database Script"""
import asyncio
import uuid
from datetime import date, timedelta
from decimal import Decimal
from app.core.database import init_db, async_session_factory
from app.models.models import Tenant, User, Department, Employee
from app.core.security import hash_password


async def seed():
    await init_db()
    async with async_session_factory() as s:
        r = await s.execute(Tenant.__table__.select().where(Tenant.slug == "demo"))
        if r.scalar_one_or_none():
            print("Already seeded.")
            return
        t = Tenant(id=uuid.uuid4(), name="شركة تجريبية", slug="demo", email="admin@demo.com", country="EG", currency="EGP", employee_count=0, max_employees=500)
        s.add(t)
        await s.flush()
        u = User(id=uuid.uuid4(), tenant_id=t.id, email="admin@demo.com", password_hash=hash_password("admin123"), full_name="Admin", role="super_admin", is_active=True, is_verified=True)
        s.add(u)
        await s.flush()
        deps = [
            Department(id=uuid.uuid4(), tenant_id=t.id, name="تطوير البرمجيات", code="DEV"),
            Department(id=uuid.uuid4(), tenant_id=t.id, name="التصميم", code="DESIGN"),
            Department(id=uuid.uuid4(), tenant_id=t.id, name="المبيعات", code="SALES"),
            Department(id=uuid.uuid4(), tenant_id=t.id, name="الموارد البشرية", code="HR"),
        ]
        for d in deps:
            s.add(d)
        await s.flush()
        data = [
            ("أحمد", "محمد", date(2023, 3, 15), "DEV", "Senior Developer", Decimal("18000")),
            ("سارة", "علي", date(2022, 6, 22), "DESIGN", "UI/UX Designer", Decimal("15000")),
            ("محمد", "صلاح", date(2021, 1, 10), "SALES", "Sales Manager", Decimal("10000")),
            ("خالد", "عبد الله", date(2022, 9, 5), "SUPPORT", "IT Support", Decimal("12000")),
        ]
        for fn, ln, hd, dn, jt, sal in data:
            d = next(x for x in deps if x.name == dn)
            e = Employee(id=uuid.uuid4(), tenant_id=t.id, employee_number=f"EMP-{t.id.hex[:6].upper()}-{uuid.uuid4().hex[:6].upper()}", first_name=fn, last_name=ln, hire_date=hd, department_id=d.id, job_title=jt, salary_base=sal, status="active")
            s.add(e)
        await s.commit()
        print(f"Seeded {len(data)} employees.")


if __name__ == "__main__":
    asyncio.run(seed())
