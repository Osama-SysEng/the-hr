"""اختبارات نظام الرواتب"""
import pytest
from decimal import Decimal


def test_egyptian_social_insurance():
    salary = Decimal("18000")
    min_wage = Decimal("3500")
    max_base = Decimal("9800")
    employee = max(0, (min(salary, max_base) - 720) * Decimal("0.11"))
    employer = max(0, (min(salary, max_base) - 720) * Decimal("0.1875"))
    assert float(employee) == 998.8
    assert float(employer) == 1702.5


def test_income_tax_brackets():
    annual = 240000
    tax = 0
    remaining = annual
    bracket1 = min(remaining, 15000)
    remaining -= bracket1
    bracket2 = min(remaining, 15000)
    tax += bracket2 * 0.10
    remaining -= bracket2
    bracket3 = min(remaining, 15000)
    tax += bracket3 * 0.15
    remaining -= bracket3
    bracket4 = min(remaining, 15000)
    tax += bracket4 * 0.20
    remaining -= bracket4
    bracket5 = min(remaining, 140000)
    tax += bracket5 * 0.225
    remaining -= bracket5
    tax += remaining * 0.25
    assert round(tax) == 48250


def test_payroll_net_calculation():
    base = Decimal("18000")
    earnings = base + base * Decimal("0.25") + base * Decimal("0.10") + base * Decimal("0.05")
    deductions = Decimal("0")
    insurance = base * Decimal("0.11") + base * Decimal("0.01")
    monthly_tax = Decimal("2687.50")
    net = earnings - deductions - insurance - monthly_tax
    assert float(net) == 20352.5
