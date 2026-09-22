"""الت tests لوحدة المصادقة"""
import pytest
from app.core.security import hash_password, verify_password, create_access_token


def test_hash_password():
    pw = "TestPassword123!"
    h = hash_password(pw)
    assert h != pw
    assert verify_password(pw, h) is True
    assert verify_password("wrong", h) is False


def test_create_access_token():
    token = create_access_token(
        subject="user123",
        tenant_id="tenant456",
        role="employee",
        employee_id="emp789",
        expires_delta=None,
    )
    assert token is not None
    assert len(token) > 0
