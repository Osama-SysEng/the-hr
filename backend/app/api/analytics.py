"""
The H.R - Analytics & Dashboard API Router
Dashboards, KPIs, Predictions, Reports
"""

from datetime import date, datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import (
    AttendanceRecord, Employee, Payroll, Tenant, Department,
    LeaveRequest, Candidate, JobPosting, InventoryProduct, StockMovement,
    Supplier, User, AnalyticsKPI, Prediction
)
import uuid


router = APIRouter(prefix="/analytics", tags=["Analytics"])


# -----------------------------------------------------------------------------
# Dashboard Router
# -----------------------------------------------------------------------------
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# -----------------------------------------------------------------------------
# Dashboard Overview
# -----------------------------------------------------------------------------
@dashboard_router.get("/overview")
async def dashboard_overview(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """لوحة التحكم الرئيسية - نظرة عامة على جميع الموديولات"""
    tenant_id = current_user["tenant_id"]
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    end_of_month = today
    start_of_year = date(today.year, 1, 1)

    # ----- Employee Stats -----
    emp_result = await db.execute(
        select(
            func.count(Employee.id).label("total"),
            func.sum(func.cast(Employee.status == "active", Integer)).label("active"),
            func.sum(func.cast(Employee.status == "on_leave", Integer)).label("on_leave"),
            func.sum(func.cast(Employee.status == "terminated", Integer)).label("terminated"),
        ).where(Employee.tenant_id == tenant_id)
    )
    emp_stats = emp_result.one()

    # ----- Attendance Stats (Today) -----
    att_result = await db.execute(
        select(
            func.count(AttendanceRecord.id).label("total"),
            func.sum(func.cast(AttendanceRecord.status == "present", Integer)).label("present"),
            func.sum(func.cast(AttendanceRecord.status == "absent", Integer)).label("absent"),
            func.sum(func.cast(AttendanceRecord.status == "late", Integer)).label("late"),
        ).where(
            and_(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.date == today,
            )
        )
    )
    att_stats = att_result.one()

    # ----- Payroll Stats (This Month) -----
    payroll_result = await db.execute(
        select(
            func.count(Payroll.id).label("total"),
            func.sum(Payroll.net_salary).label("total_net"),
            func.avg(Payroll.net_salary).label("avg_net"),
            func.sum(func.cast(Payroll.status == "paid", Integer)).label("paid"),
        ).where(
            and_(
                Payroll.tenant_id == tenant_id,
                Payroll.payroll_month == today.month,
                Payroll.payroll_year == today.year,
            )
        )
    )
    payroll_stats = payroll_result.one()

    # ----- Recruitment Stats -----
    # Open jobs
    jobs_result = await db.execute(
        select(func.count(JobPosting.id)).where(
            and_(JobPosting.tenant_id == tenant_id, JobPosting.is_active == True)
        )
    )
    open_jobs = jobs_result.scalar() or 0

    # Candidates in pipeline
    cand_result = await db.execute(
        select(func.count(Candidate.id)).where(Candidate.tenant_id == tenant_id)
    )
    total_candidates = cand_result.scalar() or 0

    # Candidates by stage
    stage_result = await db.execute(
        select(
            Candidate.stage,
            func.count(Candidate.id).label("count"),
        ).where(Candidate.tenant_id == tenant_id)
        .group_by(Candidate.stage)
    )
    candidates_by_stage = {row.stage: row.count for row in stage_result}

    # ----- Leave Stats -----
    leave_result = await db.execute(
        select(
            func.count(LeaveRequest.id).label("total"),
            func.sum(func.cast(LeaveRequest.status == "pending", Integer)).label("pending"),
            func.sum(func.cast(LeaveRequest.status == "approved", Integer)).label("approved"),
        ).where(
            and_(
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.start_date >= start_of_month,
                LeaveRequest.start_date <= end_of_month,
            )
        )
    )
    leave_stats = leave_result.one()

    # ----- Supply Chain Stats -----
    product_result = await db.execute(
        select(
            func.count(InventoryProduct.id).label("total_products"),
            func.sum(InventoryProduct.current_stock).label("total_stock"),
            func.count(InventoryProduct.sku).label("skus"),
        ).where(InventoryProduct.tenant_id == tenant_id)
    )
    product_stats = product_result.one()

    # Low stock products
    low_stock_result = await db.execute(
        select(func.count(InventoryProduct.id)).where(
            and_(
                InventoryProduct.tenant_id == tenant_id,
                InventoryProduct.current_stock <= InventoryProduct.minimum_stock,
                InventoryProduct.current_stock > 0,
                InventoryProduct.is_active == True,
            )
        )
    )
    low_stock_count = low_stock_result.scalar() or 0

    # ----- Loans Stats -----
    loans_result = await db.execute(
        select(
            func.count(EmployeeLoan.id).label("total"),
            func.sum(EmployeeLoan.amount).label("total_amount"),
            func.sum(func.cast(EmployeeLoan.status == "pending", Integer)).label("pending"),
        ).where(
            and_(
                EmployeeLoan.tenant_id == tenant_id,
                EmployeeLoan.status == "active",
            )
        )
    )
    loans_stats = loans_result.one()

    # ----- Turnover Risk (Simple Prediction) -----
    # Employees with high late attendance + low scores might be at risk
    turnover_risk = 0
    if emp_stats.total and emp_stats.total > 0:
        late_ratio = (att_stats.late or 0) / emp_stats.total
        if late_ratio > 0.15:
            turnover_risk = min(30, int(late_ratio * 100))
        turnover_risk = min(turnover_risk, 30)

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "employees": {
            "total": emp_stats.total or 0,
            "active": emp_stats.active or 0,
            "on_leave": emp_stats.on_leave or 0,
            "terminated": emp_stats.terminated or 0,
            "growth_rate": 0,  # Would compare with previous period
        },
        "attendance": {
            "today": {
                "total_records": att_stats.total or 0,
                "present": att_stats.present or 0,
                "absent": att_stats.absent or 0,
                "late": att_stats.late or 0,
                "attendance_rate": round(((att_stats.present or 0) / (emp_stats.active or 1)) * 100, 2),
            },
            "monthly_rate": 0,  # Would calculate from period data
        },
        "payroll": {
            "employees_processed": payroll_stats.total or 0,
            "total_cost": float(payroll_stats.total_net or 0),
            "average_salary": float(payroll_stats.avg_net or 0),
            "paid_count": payroll_stats.paid or 0,
            "pending_count": (payroll_stats.total or 0) - (payroll_stats.paid or 0),
        },
        "recruitment": {
            "open_jobs": open_jobs,
            "total_candidates": total_candidates,
            "candidates_by_stage": candidates_by_stage,
            "new_candidates_this_month": 0,  # Would calculate
        },
        "leaves": {
            "total_this_month": leave_stats.total or 0,
            "pending": leave_stats.pending or 0,
            "approved": leave_stats.approved or 0,
            "pending_rate": round(((leave_stats.pending or 0) / (emp_stats.active or 1)) * 100, 2),
        },
        "supply_chain": {
            "total_products": product_stats.total_products or 0,
            "total_stock_quantity": int(product_stats.total_stock or 0),
            "low_stock_products": low_stock_count,
            "total_inventory_value": 0,  # Would calculate from product prices
        },
        "loans": {
            "active_loans": loans_stats.total or 0,
            "total_outstanding": float(loans_stats.total_amount or 0),
            "pending_loans": loans_stats.pending or 0,
        },
        "alerts": {
            "turnover_risk_score": turnover_risk,
            "low_stock_alert": low_stock_count > 0,
            "pending_leaves_alert": leave_stats.pending and leave_stats.pending > 5,
            "pending_loan_applications": loans_stats.pending and loans_stats.pending > 3,
        },
    }


# -----------------------------------------------------------------------------
# Attendance Analytics
# -----------------------------------------------------------------------------
@router.get("/attendance/analytics")
async def attendance_analytics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    department_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """تحليلات الحضور والانصراف"""
    tenant_id = current_user["tenant_id"]

    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    # Base query
    query = select(
        AttendanceRecord.department_id,
        func.count(AttendanceRecord.id).label("total"),
        func.sum(func.cast(AttendanceRecord.status == "present", Integer)).label("present"),
        func.sum(func.cast(AttendanceRecord.status == "absent", Integer)).label("absent"),
        func.sum(func.cast(AttendanceRecord.status == "late", Integer)).label("late"),
        func.avg(AttendanceRecord.total_hours).label("avg_hours"),
        func.sum(AttendanceRecord.overtime_minutes).label("total_overtime"),
    ).join(
        Employee, AttendanceRecord.employee_id == Employee.id
    ).where(
        and_(
            AttendanceRecord.tenant_id == tenant_id,
            AttendanceRecord.date >= start_date,
            AttendanceRecord.date <= end_date,
        )
    )

    if department_id:
        query = query.where(Employee.department_id == department_id)

    query = query.group_by(AttendanceRecord.department_id)
    result = await db.execute(query)
    rows = result.all()

    by_department = []
    for row in rows:
        dept_name_result = await db.execute(
            select(Department.name).where(Department.id == row.department_id)
        )
        dept_name = dept_name_result.scalar() or "إدارة عامة"
        by_department.append({
            "department_id": row.department_id,
            "department_name": dept_name,
            "total": row.total,
            "present": row.present or 0,
            "absent": row.absent or 0,
            "late": row.late or 0,
            "attendance_rate": round((row.present or 0) / (row.total or 1) * 100, 2),
            "avg_hours": round(float(row.avg_hours or 0), 2),
            "total_overtime": int(row.total_overtime or 0),
        })

    # Overall stats
    overall_result = await db.execute(
        select(
            func.count(AttendanceRecord.id).label("total"),
            func.sum(func.cast(AttendanceRecord.status == "present", Integer)).label("present"),
            func.sum(func.cast(AttendanceRecord.status == "absent", Integer)).label("absent"),
            func.sum(func.cast(AttendanceRecord.status == "late", Integer)).label("late"),
            func.avg(AttendanceRecord.total_hours).label("avg_hours"),
            func.sum(AttendanceRecord.overtime_minutes).label("total_overtime"),
        ).where(
            and_(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.date >= start_date,
                AttendanceRecord.date <= end_date,
            )
        )
    )
    overall = overall_result.one()

    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "overall": {
            "total_records": overall.total,
            "present": overall.present or 0,
            "absent": overall.absent or 0,
            "late": overall.late or 0,
            "attendance_rate": round((overall.present or 0) / (overall.total or 1) * 100, 2),
            "average_hours": round(float(overall.avg_hours or 0), 2),
            "total_overtime_minutes": int(overall.total_overtime or 0),
        },
        "by_department": by_department,
    }


# -----------------------------------------------------------------------------
# Recruitment Analytics
# -----------------------------------------------------------------------------
@router.get("/recruitment/analytics")
async def recruitment_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """تحليلات التوظيف"""
    tenant_id = current_user["tenant_id"]
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    # Open positions
    jobs_result = await db.execute(
        select(
            func.count(JobPosting.id).label("total"),
            func.sum(func.cast(JobPosting.is_active == True, Integer)).label("open"),
        ).where(JobPosting.tenant_id == tenant_id)
    )
    jobs_stats = jobs_result.one()

    # Candidates
    cand_result = await db.execute(
        select(
            func.count(Candidate.id).label("total"),
            func.sum(func.cast(Candidate.stage == "hired", Integer)).label("hired"),
            func.sum(func.cast(Candidate.stage == "rejected", Integer)).label("rejected"),
            func.sum(func.cast(Candidate.stage == "new", Integer)).label("new"),
        ).where(Candidate.tenant_id == tenant_id)
    )
    cand_stats = cand_result.one()

    # Candidates by stage
    stage_result = await db.execute(
        select(
            Candidate.stage,
            func.count(Candidate.id).label("count"),
        ).where(Candidate.tenant_id == tenant_id)
        .group_by(Candidate.stage)
    )
    by_stage = {row.stage: row.count for row in stage_result}

    # Candidates by source
    source_result = await db.execute(
        select(
            Candidate.source,
            func.count(Candidate.id).label("count"),
        ).where(
            and_(
                Candidate.tenant_id == tenant_id,
                Candidate.source.isnot(None),
            )
        ).group_by(Candidate.source)
    )
    by_source = {row.source: row.count for row in source_result}

    # Recent hires this month
    hired_result = await db.execute(
        select(func.count(Candidate.id)).where(
            and_(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "hired",
                func.extract("year", Candidate.hired_at) == today.year,
                func.extract("month", Candidate.hired_at) == today.month,
            )
        )
    )
    hired_this_month = hired_result.scalar() or 0

    return {
        "positions": {
            "total": jobs_stats.total or 0,
            "open": jobs_stats.open or 0,
            "filled": (jobs_stats.total or 0) - (jobs_stats.open or 0),
        },
        "candidates": {
            "total": cand_stats.total or 0,
            "new": cand_stats.new or 0,
            "hired": cand_stats.hired or 0,
            "rejected": cand_stats.rejected or 0,
            "conversion_rate": round((cand_stats.hired or 0) / (cand_stats.total or 1) * 100, 2),
        },
        "by_stage": by_stage,
        "by_source": by_source,
        "hired_this_month": hired_this_month,
    }


# -----------------------------------------------------------------------------
# Payroll Analytics
# -----------------------------------------------------------------------------
@router.get("/payroll/analytics")
async def payroll_analytics(
    start_month: Optional[int] = Query(None),
    start_year: Optional[int] = Query(None),
    end_month: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    department_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager", "accountant")),
):
    """تحليلات الرواتب"""
    tenant_id = current_user["tenant_id"]

    if not start_month:
        start_month = date.today().month
        start_year = date.today().year
    if not end_month:
        end_month = start_month
        end_year = start_year

    # Build date range
    period_start = date(start_year, start_month, 1)
    if end_month == 12:
        period_end = date(end_year, 12, 31)
    else:
        period_end = date(end_year, end_month + 1, 1) - timedelta(days=1)

    # Base query
    query = select(
        Payroll.payroll_month,
        Payroll.payroll_year,
        func.count(Payroll.id).label("employees"),
        func.sum(Payroll.net_salary).label("total_cost"),
        func.avg(Payroll.net_salary).label("avg_salary"),
        func.sum(Payroll.base_salary).label("total_base"),
    ).where(
        and_(
            Payroll.tenant_id == tenant_id,
            Payroll.status.in_(["calculated", "approved", "paid"]),
            Payroll.payroll_year >= start_year,
            Payroll.payroll_year <= end_year,
        )
    )

    if department_id:
        query = query.join(Employee).where(Employee.department_id == department_id)

    query = query.group_by(Payroll.payroll_month, Payroll.payroll_year).order_by(
        Payroll.payroll_year, Payroll.payroll_month
    )

    result = await db.execute(query)
    rows = result.all()

    by_month = []
    total_cost = 0
    total_employees = 0
    for row in rows:
        by_month.append({
            "month": row.payroll_month,
            "year": row.payroll_year,
            "employees": row.employees,
            "total_cost": float(row.total_cost or 0),
            "average_salary": round(float(row.avg_salary or 0), 2),
            "total_base": float(row.total_base or 0),
        })
        total_cost += row.total_cost or 0
        total_employees += row.employees

    # Department breakdown
    dept_query = select(
        Employee.department_id,
        func.count(Payroll.id).label("employees"),
        func.sum(Payroll.net_salary).label("total_cost"),
        func.avg(Payroll.net_salary).label("avg_salary"),
    ).join(
        Employee, Payroll.employee_id == Employee.id
    ).where(
        and_(
            Payroll.tenant_id == tenant_id,
            Payroll.status.in_(["calculated", "approved", "paid"]),
            Payroll.payroll_year == start_year,
            Payroll.payroll_month == start_month,
        )
    )

    if department_id:
        dept_query = dept_query.where(Employee.department_id == department_id)

    dept_query = dept_query.group_by(Employee.department_id)
    dept_result = await db.execute(dept_query)
    by_department = []
    for row in dept_result:
        dept_name_result = await db.execute(
            select(Department.name).where(Department.id == row.department_id)
        )
        dept_name = dept_name_result.scalar() or "إدارة عامة"
        by_department.append({
            "department_id": row.department_id,
            "department_name": dept_name,
            "employees": row.employees,
            "total_cost": float(row.total_cost or 0),
            "average_salary": round(float(row.avg_salary or 0), 2),
        })

    return {
        "period": {
            "start": f"{start_month}/{start_year}",
            "end": f"{end_month}/{end_year}",
        },
        "summary": {
            "total_employees": total_employees,
            "total_payroll_cost": round(float(total_cost), 2),
            "average_salary": round(float(total_cost / total_employees), 2) if total_employees > 0 else 0,
            "months_count": len(by_month),
        },
        "by_month": by_month,
        "by_department": by_department,
    }


# -----------------------------------------------------------------------------
# Supply Chain Analytics
# -----------------------------------------------------------------------------
@router.get("/supply-chain/analytics")
async def supply_chain_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """تحليلات سلسلة التوريد"""
    tenant_id = current_user["tenant_id"]

    # Products stats
    product_result = await db.execute(
        select(
            func.count(InventoryProduct.id).label("total"),
            func.count(InventoryProduct.sku).label("skus"),
            func.sum(InventoryProduct.current_stock * InventoryProduct.purchase_price).label("total_value"),
            func.sum(InventoryProduct.current_stock).label("total_qty"),
            func.sum(func.cast(InventoryProduct.current_stock <= 0, Integer)).label("out_of_stock"),
            func.sum(func.cast(
                and_(
                    InventoryProduct.current_stock > 0,
                    InventoryProduct.current_stock <= InventoryProduct.minimum_stock,
                ),
                Integer
            )).label("low_stock"),
        ).where(InventoryProduct.tenant_id == tenant_id)
    )
    product_stats = product_result.one()

    # Stock movements (last 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    movements_result = await db.execute(
        select(
            StockMovement.movement_type,
            func.sum(StockMovement.quantity).label("total"),
            func.count(StockMovement.id).label("count"),
        ).where(
            and_(
                StockMovement.tenant_id == tenant_id,
                StockMovement.created_at >= thirty_days_ago,
            )
        ).group_by(StockMovement.movement_type)
    )
    movements = {row.movement_type: {"total": float(row.total or 0), "count": row.count} for row in movements_result}

    # Suppliers
    supplier_result = await db.execute(
        select(
            func.count(Supplier.id).label("total"),
            func.sum(Supplier.rating).label("avg_rating"),
        ).where(Supplier.tenant_id == tenant_id)
    )
    supplier_stats = supplier_result.one()

    # Top products by value
    top_result = await db.execute(
        select(
            InventoryProduct.name,
            InventoryProduct.sku,
            InventoryProduct.current_stock,
            InventoryProduct.purchase_price,
            func.round(InventoryProduct.current_stock * InventoryProduct.purchase_price, 2).label("value"),
        ).where(
            and_(
                InventoryProduct.tenant_id == tenant_id,
                InventoryProduct.current_stock > 0,
                InventoryProduct.purchase_price.isnot(None),
            )
        ).order_by(text("value DESC")).limit(10)
    )
    top_products = []
    for row in top_result:
        top_products.append({
            "name": row.name,
            "sku": row.sku,
            "stock": float(row.current_stock),
            "unit_price": float(row.purchase_price or 0),
            "value": float(row.value or 0),
        })

    return {
        "products": {
            "total": product_stats.total or 0,
            "skus": product_stats.skus or 0,
            "total_inventory_value": round(float(product_stats.total_value or 0), 2),
            "total_quantity": int(product_stats.total_qty or 0),
            "out_of_stock": product_stats.out_of_stock or 0,
            "low_stock": product_stats.low_stock or 0,
        },
        "movements_last_30_days": movements,
        "suppliers": {
            "total": supplier_stats.total or 0,
            "average_rating": round(float(supplier_stats.avg_rating or 0), 2),
        },
        "top_products_by_value": top_products,
    }
