"""اختبارات الأمان والـ RBAC"""
import pytest
from app.core.security import ROLE_PERMISSIONS


def test_all_roles_have_permissions():
    for role in ROLE_PERMISSIONS:
        assert len(ROLE_PERMISSIONS[role]) > 0, f"{role} has no permissions"


def test_super_admin_has_full_access():
    perms = ROLE_PERMISSIONS["super_admin"]
    assert "employees:write" in perms
    assert "payroll:write" in perms
    assert "recruitment:write" in perms
    assert "attendance:write" in perms


def test_employee_limited_access():
    perms = ROLE_PERMISSIONS["employee"]
    assert "employees:read" in perms
    assert "attendance:read" in perms
    assert "payroll:read" in perms
    assert "employees:write" not in perms
    assert "payroll:write" not in perms
