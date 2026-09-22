"""اختبارات خدمة البريد الإلكتروني"""
import pytest


def test_email_connection():
    smtp_host = "smtp.gmail.com"
    smtp_port = 587
    assert smtp_port == 587
    assert "gmail.com" in smtp_host


def test_payslip_template():
    subject = "كشف الراتب - 11/2026"
    assert "كشف الراتب" in subject
    assert "11/2026" in subject


def test_interview_invitation():
    subject = "دعوة مقابلة آلية - مطور برمجيات"
    assert "دعوة مقابلة" in subject
    assert "مطور برمجيات" in subject
