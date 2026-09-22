"""
التوسع الأفقي - تكوين (Horizontal Scaling Configuration)
يدعم:
- التوسع التلقائي (Auto-scaling)
- توازن الأحمال (Load Balancing)
- إدارة الجلسات الخارجية
- الإخطارات عند الامتلاء
"""

from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class ScalingStrategy(Enum):
    """استراتيجيات التوسع"""
    MANUAL = "manual"
    CPU_BASED = "cpu_based"
    MEMORY_BASED = "memory_based"
    REQUEST_BASED = "request_based"
    CUSTOM = "custom"


@dataclass
class AutoScalingConfig:
    """إعدادات التوسع التلقائي"""
    min_instances: int = 2
    max_instances: int = 20
    target_cpu_utilization: float = 70.0
    target_memory_utilization: float = 75.0
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.3
    scale_up_cooldown_seconds: int = 300
    scale_down_cooldown_seconds: int = 600
    scale_increment: int = 1


@dataclass
class LoadBalancerConfig:
    """إعدادات توازن الأحمال"""
    algorithm: str = "round_robin"
    health_check_interval: int = 30
    health_check_timeout: int = 5
    health_check_retries: int = 3
    unhealthy_threshold: int = 3
    sticky_sessions: bool = False
    session_timeout: int = 3600


@dataclass
class SessionConfig:
    """إعدادات إدارة الجلسات في البيئة الموزعة"""
    external_storage: bool = True
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    session_timeout_minutes: int = 60
    refresh_threshold_minutes: int = 30


DEFAULT_AUTO_SCALING = AutoScalingConfig(
    min_instances=2,
    max_instances=20,
    target_cpu_utilization=70.0,
    target_memory_utilization=75.0,
)

DEFAULT_LOAD_BALANCER = LoadBalancerConfig(
    algorithm="round_robin",
    health_check_interval=30,
    health_check_timeout=5,
    sticky_sessions=False,
)

DEFAULT_SESSION = SessionConfig(
    external_storage=True,
    session_timeout_minutes=60,
)


class ScalingManager:
    """مدير التوسع الأفقي"""

    def __init__(self, config: AutoScalingConfig = None):
        self.config = config or DEFAULT_AUTO_SCALING
        self.current_instances = self.config.min_instances
        self.last_scale_time: float = 0
        self.metrics_history: List[Dict] = []

    def should_scale_up(self, current_metrics: Dict) -> bool:
        """تحديد ما إذا كان يجب التوسع"""
        import time
        now = time.time()
        if now - self.last_scale_time < self.config.scale_up_cooldown_seconds:
            return False

        cpu = current_metrics.get("cpu_percent", 0)
        memory = current_metrics.get("memory_percent", 0)

        if cpu > self.config.target_cpu_utilization * self.config.scale_up_threshold:
            return True
        if memory > self.config.target_memory_utilization * self.config.scale_up_threshold:
            return True

        return False

    def should_scale_down(self, current_metrics: Dict) -> bool:
        """تحديد ما إذا كان يجب الانكماش"""
        import time
        now = time.time()
        if now - self.last_scale_time < self.config.scale_down_cooldown_seconds:
            return False

        cpu = current_metrics.get("cpu_percent", 0)
        memory = current_metrics.get("memory_percent", 0)

        if cpu < self.config.target_cpu_utilization * self.config.scale_down_threshold:
            if memory < self.config.target_memory_utilization * self.config.scale_down_threshold:
                return True

        return False

    async def scale(self, target_instances: int) -> bool:
        """تغيير عدد الحالات النشطة"""
        import time
        if target_instances < self.config.min_instances:
            target_instances = self.config.min_instances
        if target_instances > self.config.max_instances:
            target_instances = self.config.max_instances

        if target_instances == self.current_instances:
            return False

        self.current_instances = target_instances
        self.last_scale_time = time.time()
        return True

    def record_metrics(self, metrics: Dict) -> None:
        """تسجيل مقياس جديد"""
        import time
        self.metrics_history.append({
            **metrics,
            "timestamp": time.time()
        })
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]


SCALING_CHECKPOINTS = {
    "api_requests_per_second": "معدل طلبات واجهة التطبيق",
    "celery_queue_length": "طول قائمة مهام Celery",
    "database_connections_active": "الاتصالات النشطة بقاعدة البيانات",
    "redis_memory_usage": "استخدام ذاكرة Redis",
    "response_time_p95": "وقت الاستجابة (الـ 95th percentile)",
    "error_rate": "معدل الأخطاء",
}
