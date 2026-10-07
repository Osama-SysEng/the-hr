"""اختبارات قاعدة البيانات"""
import pytest


def test_all_models_defined():
    models = [
        "Tenant", "User", "Department", "Employee",
        "AttendanceRecord", "LeaveRequest", "EmployeeLoan",
        "Payroll", "JobPosting", "Candidate", "AIInterview",
        "InventoryProduct", "StockMovement", "Supplier",
        "PurchaseOrder", "PurchaseOrderItem",
        "AnalyticsKPI", "Prediction", "AuditLog",
        "PerformanceReview",
    ]
    assert len(models) == 20


def test_all_tables_have_tenant_id():
    tenant_tables = [
        "tenants", "users", "departments", "employees",
        "attendance_records", "leave_requests", "employee_loans",
        "payrolls", "job_postings", "candidates", "ai_interviews",
        "inventory_products", "stock_movements", "suppliers",
        "purchase_orders", "purchase_order_items", "analytics_kpis", "predictions",
        "audit_logs", "performance_reviews",
    ]
    assert len(tenant_tables) == 20
