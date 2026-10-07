"""اختبارات الموظفين"""
import pytest


def test_full_name():
    emp = {"first_name": "أحمد", "last_name": "محمد"}
    assert f"{emp['first_name']} {emp['last_name']}" == "أحمد محمد"


def test_employee_number():
    tenant_hex = "abcd1234"
    emp_id = "ef567890"
    number = f"EMP-{tenant_hex[:6].upper()}-{emp_id[:6].upper()}"
    assert number == "EMP-ABCD12-EF5678"


def test_salary_calculation():
    base = 18000
    housing = base * 0.25
    transport = base * 0.10
    total = base + housing + transport
    assert total == 24300
