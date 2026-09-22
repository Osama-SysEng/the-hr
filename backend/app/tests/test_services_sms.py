"""اختبارات خدمة الرسائل النصية"""
import pytest


def test_sms_template():
    template = "[{status}] {name}: {details}"
    result = template.format(status="حاضر", name="أحمد", details="08:42 AM")
    assert "حاضر" in result
    assert "أحمد" in result


def test_bulk_sms():
    recipients = [
        {"phone": "+201234567890", "name": "أحمد"},
        {"phone": "+201987654321", "name": "سارة"},
    ]
    assert len(recipients) == 2
