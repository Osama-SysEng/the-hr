#!/usr/bin/env python
"""The H.R - Cleanup Script"""
import asyncio
from datetime import date, timedelta
from app.core.database import async_session_factory
from app.models.models import AttendanceRecord, AuditLog


async def cleanup(days=90):
    await init_db()
    async with async_session_factory() as s:
        cutoff = date.today() - timedelta(days=days)
        for model in [AttendanceRecord, AuditLog]:
            r = await s.execute(model.__table__.delete().where(model.date < cutoff))
            await s.commit()
            print(f"Cleaned {r.rowcount} {model.__tablename__}")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(cleanup())
