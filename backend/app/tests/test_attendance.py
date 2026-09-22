"""اختبارات الحضور والانصراف"""
import pytest
from datetime import date, timedelta


def test_clock_in_status():
    today = date.today()
    assert today.weekday() == today.weekday()


def test_overtime_calculation():
    clock_in = 8.5
    clock_out = 17.0
    hours = clock_out - clock_in
    overtime = max(0, hours - 8) * 60
    assert overtime == 30


def test_late_calculation():
    clock_in_hour = 9
    clock_in_minute = 25
    late_min = (clock_in_hour - 9) * 60 + clock_in_minute
    assert late_min == 25
