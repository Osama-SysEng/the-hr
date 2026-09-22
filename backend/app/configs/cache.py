"""
إدارة التخزين المؤقت (Caching Layer)
يدعم:
- Redis cache (تخزين مشترك بين العمال)
- Memcached (بديل)
- في الذاكرة (للعامل الواحد)
- استراتيجيات invalidation الذكية
- TTL قابل للتعديل
"""

from typing import Any, Optional, Dict
from datetime import timedelta
import json
import asyncio


class CacheManager:
    """مدير التخزين المؤقت الرئيسي"""

    def __init__(self, redis_client=None, use_memory: bool = False):
        self.redis = redis_client
        self.use_memory = use_memory
        self._memory_cache: Dict[str, dict] = {}
        self._ttl_defaults = {
            "tenant_settings": 3600,
            "company_info": 1800,
            "user_profile": 600,
            "attendance_summary": 300,
            "payroll_preview": 120,
            "recruitment_stats": 600,
            "inventory_snapshot": 300,
            "analytics_dashboard": 300,
            "ai_cached_result": 86400,
        }

    def _make_key(self, tenant_id: str, key: str) -> str:
        return f"tenant:{tenant_id}:cache:{key}"

    async def get(self, tenant_id: str, key: str, default: Any = None) -> Any:
        cache_key = self._make_key(tenant_id, key)

        if self.use_memory:
            if cache_key in self._memory_cache:
                entry = self._memory_cache[cache_key]
                if __import__('time').time() < entry["expires_at"]:
                    return entry["value"]
                del self._memory_cache[cache_key]
            return default

        if self.redis:
            data = await self.redis.get(cache_key)
            if data:
                return json.loads(data)
            return default

        return default

    async def set(
        self,
        tenant_id: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        cache_key = self._make_key(tenant_id, key)
        ttl = ttl_seconds or self._ttl_defaults.get(key, 300)
        expires_at = __import__('time').time() + ttl

        entry = {"value": value, "expires_at": expires_at}

        if self.use_memory:
            self._memory_cache[cache_key] = entry
            return

        if self.redis:
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(value, default=str)
            )

    async def delete(self, tenant_id: str, key: str) -> None:
        cache_key = self._make_key(tenant_id, key)

        if self.use_memory:
            self._memory_cache.pop(cache_key, None)
            return

        if self.redis:
            await self.redis.delete(cache_key)

    async def clear_tenant(self, tenant_id: str) -> None:
        pattern = f"tenant:{tenant_id}:cache:*"

        if self.use_memory:
            keys_to_delete = [
                k for k in self._memory_cache
                if k.startswith(f"tenant:{tenant_id}:cache:")
            ]
            for key in keys_to_delete:
                del self._memory_cache[key]
            return

        if self.redis:
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)

    async def get_or_set(
        self,
        tenant_id: str,
        key: str,
        fetch_func,
        ttl_seconds: Optional[int] = None
    ) -> Any:
        cached = await self.get(tenant_id, key)
        if cached is not None:
            return cached

        value = await fetch_func()
        await self.set(tenant_id, key, value, ttl_seconds)
        return value

    def invalidate_pattern(self, tenant_id: str, pattern: str) -> None:
        if self.use_memory:
            keys_to_delete = [
                k for k in self._memory_cache
                if pattern in k
            ]
            for key in keys_to_delete:
                del self._memory_cache[key]


CACHE_KEYS = {
    "tenant_settings": "settings",
    "company_profile": "company",
    "departments": "departments",
    "leave_types": "leave_types",
    "payroll_calendar": "payroll_calendar",
    "attendance_summary_today": "attendance:today",
    "dashboard_stats": "dashboard:stats",
    "recruitment_pipeline": "recruitment:pipeline",
    "inventory_levels": "inventory:levels",
}

CACHE_TTLS = {
    "auth_tokens": 900,
    "session_data": 1800,
    "permissions": 3600,
    "notifications": 60,
    "real_time_attendance": 30,
    "reports": 3600,
    "exports": 1800,
}

CACHE_SIZE_LIMITS = {
    "per_tenant": 1000,
    "total_memory": 256 * 1024 * 1024,
    "max_single_value": 1 * 1024 * 1024,
}
