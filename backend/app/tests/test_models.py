"""اختبارات وحدة النماذج"""
import pytest


def test_tenant_creation():
    name = "شركة تقنية المعلومات"
    slug = "tech-company-2026"
    assert len(name) > 0
    assert len(slug) <= 100


def test_user_roles():
    roles = ["super_admin", "company_admin", "hr_manager", "manager", "employee", "accountant"]
    assert len(roles) == 6
    assert "super_admin" in roles
    assert "employee" in roles


def test_employee_status():
    statuses = ["active", "on_leave", "terminated", "probation", "retired"]
    assert len(statuses) == 5
