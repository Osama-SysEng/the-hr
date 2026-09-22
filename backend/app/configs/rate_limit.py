"""
معدلات الحد من الطلبات (Rate Limiting)
يدعم أنماط متعددة: حسب الدور, النهاية, المستخدم, IP
والتكلفة المتغيرة (sliding window)
"""

from datetime import timedelta
from typing import Dict, Optional


ROLE_LIMITS: Dict[str, Dict[str, int]] = {
    "super_admin": {"requests_per_minute": 1200, "requests_per_hour": 10000},
    "admin": {"requests_per_minute": 600, "requests_per_hour": 5000},
    "hr_manager": {"requests_per_minute": 400, "requests_per_hour": 3000},
    "manager": {"requests_per_minute": 300, "requests_per_hour": 2000},
    "employee": {"requests_per_minute": 200, "requests_per_hour": 1000},
    "accountant": {"requests_per_minute": 250, "requests_per_hour": 1500},
}

ENDPOINT_LIMITS: Dict[str, Dict[str, int]] = {
    "/api/auth/login": {"requests_per_minute": 10, "requests_per_hour": 50},
    "/api/auth/register": {"requests_per_minute": 5, "requests_per_hour": 20},
    "/api/attendance/face-recognition": {"requests_per_minute": 30, "requests_per_hour": 200},
    "/api/recruitment/ai-screen": {"requests_per_minute": 60, "requests_per_hour": 500},
    "/api/recruitment/ai-interview": {"requests_per_minute": 20, "requests_per_hour": 100},
}

GLOBAL_LIMITS: Dict[str, int] = {
    "requests_per_second": 200,
    "burst_limit": 50,
}

SLIDING_WINDOW_SECONDS = 60
ABUSE_DETECTION = {
    "max_failed_logins": 5,
    "lockout_duration_minutes": 30,
    "suspicious_ip_threshold": 100,
    "auto_block_duration_hours": 2,
}


class RateLimiter:
    """مدير معدلات الحد من الطلبات

    يدعم التخزين في الذاكرة أو Redis
    """

    def __init__(self, use_redis: bool = False):
        self.use_redis = use_redis
        self._local_cache: Dict[str, list] = {}
        self._abuse_tracker: Dict[str, dict] = {}

    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """تحقق مما إذا كان الطلب مسموحًا به"""
        import time
        now = time.time()
        window_start = now - window_seconds

        if key not in self._local_cache:
            self._local_cache[key] = []

        self._local_cache[key] = [ts for ts in self._local_cache[key] if ts > window_start]

        if len(self._local_cache[key]) >= limit:
            return False

        self._local_cache[key].append(now)
        return True

    def get_remaining(self, key: str, limit: int, window_seconds: int = 60) -> int:
        """عدد الطلبات المتبقية"""
        import time
        now = time.time()
        window_start = now - window_seconds

        if key not in self._local_cache:
            return limit

        self._local_cache[key] = [ts for ts in self._local_cache[key] if ts > window_start]
        return max(0, limit - len(self._local_cache[key]))

    def check_abuse(self, identifier: str) -> dict:
        """كشف النشاط المشبوه"""
        import time
        now = time.time()
        minute_ago = now - 60

        if identifier not in self._abuse_tracker:
            self._abuse_tracker[identifier] = {
                "request_count": 0,
                "failed_logins": 0,
                "first_seen": now,
                "blocked_until": 0,
                "is_blocked": False,
            }

        tracker = self._abuse_tracker[identifier]
        if tracker["blocked_until"] > now:
            return {"allowed": False, "reason": "blocked", "blocked_until": tracker["blocked_until"]}

        tracker["request_count"] += 1
        return {"allowed": True, "count": tracker["request_count"]}


class RateLimitMiddleware:
    """Middleware لإضافة rate limiting إلى FastAPI"""

    def __init__(self, limiter: RateLimiter):
        self.limiter = limiter

    async def check_rate_limit(self, request, role: str = "employee") -> dict:
        """التحقق من الحد الأقصى للطلب"""
        identifier = f"{role}:{request.client.host if request.client else 'unknown'}"
        limits = ROLE_LIMITS.get(role, ROLE_LIMITS["employee"])
        allowed = self.limiter.is_allowed(
            identifier, limits["requests_per_minute"], SLIDING_WINDOW_SECONDS
        )
        remaining = self.limiter.get_remaining(
            identifier, limits["requests_per_minute"], SLIDING_WINDOW_SECONDS
        )

        return {
            "allowed": allowed,
            "remaining": remaining,
            "limit": limits["requests_per_minute"],
            "reset_in": SLIDING_WINDOW_SECONDS,
            "role": role,
        }
