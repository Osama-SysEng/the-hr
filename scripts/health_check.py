#!/usr/bin/env python
"""The H.R - Health Check Script"""
import sys
import asyncio
from app.core.database import async_session_factory
from app.models.models import Tenant


async def check():
    async with async_session_factory() as s:
        r = await s.execute(Tenant.__table__.select().limit(1))
        return r.scalar_one_or_none() is not None


if __name__ == "__main__":
    ok = asyncio.run(check())
    sys.exit(0 if ok else 1)
