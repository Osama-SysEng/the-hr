"""اختبارات التحليلات والتنبؤات"""
import pytest


def test_turnover_risk():
    risk = 0
    late = 20
    total = 100
    if late / total > 0.15:
        risk += 20
    years = 1
    if years < 2:
        risk += 10
    if years > 5:
        risk -= 10
    assert risk == 30


def test_payroll_forecast():
    current = 100000
    growth = 0.02
    for m in range(1, 4):
        projected = current * ((1 + growth) ** m)
    assert round(projected, 2) == 106120.80
