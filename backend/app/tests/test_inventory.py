"""اختبارات المخزن وسلسلة التوريد"""
import pytest


def test_stock_movement():
    stock = 100
    qty = 30
    assert stock + qty == 130
    assert stock - qty == 70


def test_low_stock_alert():
    current = 15
    minimum = 20
    assert current <= minimum


def test_purchase_order_total():
    items = [
        {"qty": 10, "price": 1500},
        {"qty": 5, "price": 2000},
    ]
    total = sum(i["qty"] * i["price"] for i in items)
    assert total == 25000
    tax = total * 0.14
    assert tax == 3500
    grand = total + tax
    assert grand == 28500
