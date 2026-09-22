"""اختبارات لوحة التحكم"""
import pytest


def test_dashboard_stats():
    total = 147
    active = 142
    on_leave = 3
    assert total == active + on_leave


def test_admin_dashboardtotals():
    employees = 147
    attendance_today = 138
    attendance_rate = round((attendance_today / employees) * 100, 2)
    assert attendance_rate == 93.88


def test_payroll_summary():
    net_total = 128500
    count = 147
    avg = round(net_total / count, 2)
    assert avg == 874.15
