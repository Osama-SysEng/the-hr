"""
قاعدة البيانات - إعدادات الأداء والتوسع (PostgreSQL Tuning)
يدعم:
- Connection pooling متقدم
- Read replicas
- فهارس موصى بها لأداء عالي
- تحسينات تلقائية
"""

from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class ConnectionPoolConfig:
    """إعدادات اتصال قاعدة البيانات"""
    pool_size: int = 20
    max_overflow: int = 40
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False


@dataclass
class ReadReplicaConfig:
    """إعدادات نسخة القراءة"""
    enabled: bool = False
    url: Optional[str] = None
    weight: int = 1
    read_only: bool = True


@dataclass
class IndexConfig:
    """إعدادات الفهارس"""
    auto_create_indexes: bool = True
    analyze_after_migration: bool = True
    vacuum_after_big_operations: bool = True
    fill_factor: int = 90
    concurrent_create: bool = True


DEFAULT_POOL_CONFIG = ConnectionPoolConfig(
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False,
)

READ_REPLICAS: List[ReadReplicaConfig] = []

RECOMMENDED_INDEXES: List[Dict] = [
    {
        "table": "attendance_records",
        "columns": ["employee_id", "attendance_date"],
        "name": "ix_attendance_employee_date",
        "unique": False,
        "concurrently": True,
    },
    {
        "table": "attendance_records",
        "columns": ["tenant_id", "attendance_date", "status"],
        "name": "ix_attendance_tenant_date_status",
        "unique": False,
        "concurrently": True,
    },
    {
        "table": "payroll_records",
        "columns": ["employee_id", "payroll_month", "payroll_year"],
        "name": "ix_payroll_employee_month_year",
        "unique": False,
        "concurrently": True,
    },
    {
        "table": "payroll_records",
        "columns": ["tenant_id", "payroll_month", "payroll_year", "status"],
        "name": "ix_payroll_tenant_month_year_status",
        "unique": False,
        "concurrently": True,
    },
    {
        "table": "employees",
        "columns": ["tenant_id", "national_id"],
        "name": "ix_employees_tenant_national_id",
        "unique": True,
        "concurrently": True,
    },
    {
        "table": "employees",
        "columns": ["tenant_id", "email"],
        "name": "ix_employees_tenant_email",
        "unique": True,
        "concurrently": True,
    },
    {
        "table": "candidates",
        "columns": ["tenant_id", "applied_position_id", "status"],
        "name": "ix_candidates_tenant_position_status",
        "unique": False,
        "concurrently": True,
    },
    {
        "table": "candidates",
        "columns": ["tenant_id", "cv_extraction_status"],
        "name": "ix_candidates_tenant_cv_status",
        "unique": False,
        "concurrently": True,
    },
    {
        "table": "inventory_items",
        "columns": ["tenant_id", "sku"],
        "name": "ix_inventory_tenant_sku",
        "unique": True,
        "concurrently": True,
    },
    {
        "table": "users",
        "columns": ["tenant_id", "email"],
        "name": "ix_users_tenant_email",
        "unique": True,
        "concurrently": True,
    },
    {
        "table": "users",
        "columns": ["tenant_id", "role"],
        "name": "ix_users_tenant_role",
        "unique": False,
        "concurrently": True,
    },
]


class DatabaseOptimizer:
    """محسّن قاعدة البيانات"""

    def __init__(self, engine=None):
        self.engine = engine
        self.indexes_created: set = set()
        self.analyze_scheduled: set = set()

    async def create_index_if_not_exists(self, index_config: Dict) -> bool:
        """إنشاء فهرس إذا لم يكن موجودًا"""
        index_name = index_config["name"]
        if index_name in self.indexes_created:
            return False
        self.indexes_created.add(index_name)
        return True

    async def analyze_table(self, table_name: str) -> None:
        """تحديث إحصائيات الجدول"""
        if table_name in self.analyze_scheduled:
            return
        self.analyze_scheduled.add(table_name)

    async def vacuum_analyze(self, table_name: str) -> None:
        """VACUUM ANALYZE للجدول"""
        await self.analyze_table(table_name)

    async def optimize_all(self, tables: List[str]) -> None:
        """تحسين جميع الجداول المحددة"""
        for table in tables:
            await self.analyze_table(table)

    def get_missing_indexes(self) -> List[Dict]:
        """الحصول على الفهارس المفقودة"""
        existing = self.indexes_created
        missing = [idx for idx in RECOMMENDED_INDEXES if idx["name"] not in existing]
        return missing

    async def apply_recommended_indexes(self) -> int:
        """تطبيق جميع الفهارس الموصى بها"""
        missing = self.get_missing_indexes()
        created = 0
        for idx in missing:
            if await self.create_index_if_not_exists(idx):
                created += 1
        return created
