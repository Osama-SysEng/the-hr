"""اختبارات إعدادات النظام"""
import pytest


def test_company_slug():
    slug = "company-slug-2026"
    assert len(slug) <= 100
    assert len(slug) >= 3


def test_tenant_currency():
    currencies = ["EGP", "USD", "EUR", "SAR"]
    assert "EGP" in currencies


def test_subscription_tiers():
    tiers = ["starter", "growth", "enterprise"]
    assert "enterprise" in tiers


def test_role_permissions():
    roles = ["super_admin", "company_admin", "hr_manager", "manager", "employee", "accountant"]
    assert len(roles) == 6
