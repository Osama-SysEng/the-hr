"""
The H.R - Dashboard API Router
Combined dashboard endpoints for different roles
"""

from datetime import date, datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import (
    AttendanceRecord, Employee, Payroll, Tenant, Department,
    LeaveRequest, Candidate, JobPosting, InventoryProduct
)


dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# -----------------------------------------------------------------------------
# Admin Dashboard
# -----------------------------------------------------------------------------
@dashboard_router.get("/admin")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin")),
):
    """لوحة تحكم المشرف - ملخص شامل"""
    tenant_id = current_user["tenant_id"]
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    # Employees
    emp_result = await db.execute(
        select(
            func.count(Employee.id).label("total"),
            func.sum(func.cast(Employee.status == "active", Integer)).label("active"),
            func.sum(func.cast(Employee.status == "on_leave", Integer)).label("on_leave"),
        ).where(Employee.tenant_id == tenant_id)
    )
    emp = emp_result.one()

    # Attendance today
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
    att = att_result.one()

    # Payroll this month
    payroll_result = await db.execute(
        select(
            func.count(Payroll.id).label("total"),
            func.sum(Payroll.net_salary).label("total_cost"),
            func.avg(Payroll.net_salary).label("avg_salary"),
        ).where(
            and_(
                Payroll.tenant_id == tenant_id,
                Payroll.payroll_month == today.month,
                Payroll.payroll_year == today.year,
                Payroll.status.in_(["calculated", "approved", "paid"]),
            )
        )
    )
    payroll = payroll_result.one()

    # Recruitment
    jobs_result = await db.execute(
        select(func.count(JobPosting.id)).where(
            and_(JobPosting.tenant_id == tenant_id, JobPosting.is_active == True)
        )
    )
    open_jobs = jobs_result.scalar() or 0

    cand_result = await db.execute(
        select(func.count(Candidate.id)).where(Candidate.tenant_id == tenant_id)
    )
    total_candidates = cand_result.scalar() or 0

    # Leaves
    leave_result = await db.execute(
        select(
            func.count(LeaveRequest.id).label("total"),
            func.sum(func.cast(LeaveRequest.status == "pending", Integer)).label("pending"),
        ).where(
            and_(
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.start_date >= start_of_month,
                LeaveRequest.start_date <= today,
            )
        )
    )
    leaves = leave_result.one()

    # Inventory
    product_result = await db.execute(
        select(
            func.count(InventoryProduct.id).label("total"),
            func.sum(func.cast(
                and_(
                    InventoryProduct.current_stock <= InventoryProduct.minimum_stock,
                    InventoryProduct.current_stock > 0,
                ),
                Integer
            )).label("low_stock"),
            func.sum(InventoryProduct.current_stock * InventoryProduct.purchase_price).label("total_value"),
        ).where(InventoryProduct.tenant_id == tenant_id)
    )
    products = product_result.one()

    return {
        "employees": {
            "total": emp.total or 0,
            "active": emp.active or 0,
            "on_leave": emp.on_leave or 0,
        },
        "attendance_today": {
            "total_records": att.total or 0,
            "present": att.present or 0,
            "absent": att.absent or 0,
            "late": att.late or 0,
            "attendance_rate": round(((att.present or 0) / max(emp.active or 1, 1)) * 100, 2),
        },
        "payroll_this_month": {
            "total_cost": float(payroll.total_cost or 0),
            "average_salary": round(float(payroll.avg_salary or 0), 2),
            "employees_processed": payroll.total or 0,
        },
        "recruitment": {
            "open_jobs": open_jobs,
            "total_candidates": total_candidates,
        },
        "leaves_this_month": {
            "total": leaves.total or 0,
            "pending": leaves.pending or 0,
        },
        "inventory": {
            "total_products": products.total or 0,
            "low_stock": products.low_stock or 0,
            "total_value": round(float(products.total_value or 0), 2),
        },
    }


# -----------------------------------------------------------------------------
# HR Manager Dashboard
# -----------------------------------------------------------------------------
@dashboard_router.get("/hr")
async def hr_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("hr_manager")),
):
    """لوحة تحكم موظف الموارد البشرية"""
    tenant_id = current_user["tenant_id"]
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    # Pending leaves
    pending_leaves_result = await db.execute(
        select(LeaveRequest).where(
            and_(
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.status == "pending",
                LeaveRequest.start_date >= start_of_month,
            )
        ).order_by(LeaveRequest.start_date)
    )
    pending_leaves = pending_leaves_result.scalars().all()

    # Pending candidates
    pending_cand_result = await db.execute(
        select(Candidate).where(
            and_(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "new",
            )
        ).order_by(Candidate.created_at.desc()).limit(10)
    )
    pending_candidates = pending_cand_result.scalars().all()

    # Attendance needs review
    needs_review_result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.date == today,
                AttendanceRecord.status == "late",
            )
        ).options(selectinload(AttendanceRecord.employee))
    )
    late_today = needs_review_result.scalars().all()

    # Payroll to process
    payroll_to_process_result = await db.execute(
        select(Payroll).where(
            and_(
                Payroll.tenant_id == tenant_id,
                Payroll.payroll_month == today.month,
                Payroll.payroll_year == today.year,
                Payroll.status == "calculated",
            )
        ).options(selectinload(Payroll.employee))
    )
    payroll_pending = payroll_to_process_result.scalars().all()

    return {
        "pending_leaves": [
            {
                "id": leave.id,
                "employee_name": f"{leave.employee.first_name} {leave.employee.last_name}",
                "employee_number": leave.employee.employee_number,
                "leave_type": leave.leave_type,
                "start_date": leave.start_date,
                "end_date": leave.end_date,
                "total_days": leave.total_days,
                "reason": leave.reason,
                "created_at": leave.created_at,
            }
            for leave in pending_leaves
        ],
        "pending_candidates": [
            {
                "id": cand.id,
                "name": f"{cand.first_name} {cand.last_name}",
                "email": cand.email,
                "current_position": cand.current_position,
                "current_company": cand.current_company,
                "years_experience": cand.years_experience,
                "cv_score": cand.cv_score,
                "stage": cand.stage,
                "source": cand.source,
                "cv_url": cand.cv_url,
            }
            for cand in pending_candidates
        ],
        "late_today": [
            {
                "employee_name": f"{att.employee.first_name} {att.employee.last_name}",
                "employee_number": att.employee.employee_number,
                "clock_in": att.clock_in,
                "late_minutes": att.late_minutes,
            }
            for att in late_today
        ],
        "payroll_to_approve": [
            {
                "id": payroll.id,
                "employee_name": f"{payroll.employee.first_name} {payroll.employee.last_name}",
                "employee_number": payroll.employee.employee_number,
                "net_salary": float(payroll.net_salary or 0),
                "period": f"{payroll.payroll_month}/{payroll.payroll_year}",
                "calculated_at": payroll.calculated_at,
            }
            for payroll in payroll_pending
        ],
    }


# -----------------------------------------------------------------------------
# Manager Dashboard
# -----------------------------------------------------------------------------
@dashboard_router.get("/manager")
async def manager_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """لوحة تحكم مدير القسم"""
    tenant_id = current_user["tenant_id"]
    employee_id = current_user.get("employee_id")

    if not employee_id:
        return {"message": "غير مسجل كمدر"}

    # Get manager's department
    emp_result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    manager = emp_result.scalar_one_or_none()

    if not manager:
        return {"message": "الموظف غير موجود"}

    manager_department_id = manager.department_id

    # Team attendance today
    team_att_result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.date == today,
                AttendanceRecord.employee_id.in_(
                    select(Employee.id).where(
                        and_(
                            Employee.tenant_id == tenant_id,
                            Employee.department_id == manager_department_id,
                        )
                    )
                ),
            )
        ).options(selectinload(AttendanceRecord.employee))
    )
    team_today = team_att_result.scalars().all()

    # Team pending leave requests
    team_leaves_result = await db.execute(
        select(LeaveRequest).where(
            and_(
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.status == "pending",
                LeaveRequest.employee_id.in_(
                    select(Employee.id).where(
                        and_(
                            Employee.tenant_id == tenant_id,
                            Employee.department_id == manager_department_id,
                        )
                    )
                ),
            )
        ).options(selectinload(LeaveRequest.employee))
    )
    team_pending_leaves = team_leaves_result.scalars().all()

    # Team members count
    team_count_result = await db.execute(
        select(func.count(Employee.id)).where(
            and_(
                Employee.tenant_id == tenant_id,
                Employee.department_id == manager_department_id,
                Employee.status == "active",
            )
        )
    )
    team_count = team_count_result.scalar() or 0

    return {
        "department": {
            "id": manager_department_id,
            "name": manager.department.name if manager.department else "إدارة عامة",
        },
        "team_count": team_count,
        "team_attendance_today": {
            "total": len(team_today),
            "present": sum(1 for t in team_today if t.status == "present"),
            "absent": sum(1 for t in team_today if t.status == "absent"),
            "late": sum(1 for t in team_today if t.status == "late"),
        },
        "team_attendance_details": [
            {
                "employee_name": f"{att.employee.first_name} {att.employee.last_name}",
                "employee_number": att.employee.employee_number,
                "status": att.status,
                "clock_in": att.clock_in,
                "clock_out": att.clock_out,
                "total_hours": att.total_hours,
                "late_minutes": att.late_minutes,
            }
            for att in team_today
        ],
        "pending_leave_requests": [
            {
                "id": leave.id,
                "employee_name": f"{leave.employee.first_name} {leave.employee.last_name}",
                "employee_number": leave.employee.employee_number,
                "leave_type": leave.leave_type,
                "start_date": leave.start_date,
                "end_date": leave.end_date,
                "total_days": leave.total_days,
                "reason": leave.reason,
            }
            for leave in team_pending_leaves
        ],
    }


# -----------------------------------------------------------------------------
# Employee Dashboard (Self-Service)
# -----------------------------------------------------------------------------
@dashboard_router.get("/employee")
async def employee_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """لوحة الموظف (الخدمات الذاتية)"""
    employee_id = current_user.get("employee_id")
    tenant_id = current_user["tenant_id"]
    today = date.today()

    if not employee_id:
        return {
            "message": "ليس لديك حساب موظف",
            "my_data": None,
        }

    # Get employee data
    emp_result = await db.execute(
        select(Employee)
        .where(and_(Employee.id == employee_id, Employee.tenant_id == tenant_id))
        .options(selectinload(Employee.department))
    )
    employee = emp_result.scalar_one_or_none()

    if not employee:
        return {
            "message": "بيانات الموظف غير موجودة",
            "my_data": None,
        }

    # Today's attendance
    att_result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date == today,
            )
        )
    )
    today_att = att_result.scalar_one_or_none()

    # This month's attendance
    month_start = date(today.year, today.month, 1)
    month_att_result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date >= month_start,
                AttendanceRecord.date <= today,
            )
        )
    )
    month_att = month_att_result.scalars().all()

    # Payrolls (this year)
    payroll_result = await db.execute(
        select(Payroll).where(
            and_(
                Payroll.employee_id == employee_id,
                Payroll.payroll_year == today.year,
                Payroll.status.in_(["calculated", "approved", "paid"]),
            )
        ).order_by(Payroll.payroll_month.desc())
    )
    payrolls = payroll_result.scalars().all()

    # Leave balance
    leave_result = await db.execute(
        select(LeaveRequest).where(
            and_(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.status == "approved",
                LeaveRequest.start_date >= month_start,
                LeaveRequest.start_date <= today,
            )
        )
    )
    leaves_used = leave_result.scalars().all()

    # Pending leave requests
    pending_leave_result = await db.execute(
        select(LeaveRequest).where(
            and_(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.status == "pending",
            )
        )
    )
    pending_leaves = pending_leave_result.scalars().all()

    # Pending loans
    pending_loan_result = await db.execute(
        select(EmployeeLoan).where(
            and_(
                EmployeeLoan.employee_id == employee_id,
                EmployeeLoan.tenant_id == tenant_id,
                EmployeeLoan.status == "pending",
            )
        )
    )
    pending_loans = pending_loan_result.scalars().all()

    # Active loans
    active_loans_result = await db.execute(
        select(EmployeeLoan).where(
            and_(
                EmployeeLoan.employee_id == employee_id,
                EmployeeLoan.tenant_id == tenant_id,
                EmployeeLoan.status == "active",
            )
        ).order_by(EmployeeLoan.repayment_start.desc())
    )
    active_loans = active_loans_result.scalars().all()

    # Calculate leave balance (simplified)
    if employee.hire_date:
        service_days = (today - employee.hire_date).days
        service_years = service_days / 365
        annual_entitlement = min(30, max(15, int(service_years * 25)))
    else:
        annual_entitlement = 21

    used_leaves = len(leaves_used)
    remaining_annual = annual_entitlement - used_leaves

    # Newest payroll
    latest_payroll = payrolls[0] if payrolls else None

    return {
        "my_data": {
            "id": employee.id,
            "employee_number": employee.employee_number,
            "full_name": f"{employee.first_name} {employee.last_name}",
            "job_title": employee.job_title,
            "department": {
                "id": employee.department_id,
                "name": employee.department.name if employee.department else None,
            },
            "hire_date": employee.hire_date,
            "status": employee.status,
        },
        "today_attendance": {
            "date": today_att.date if today_att else today,
            "clock_in": today_att.clock_in if today_att else None,
            "clock_out": today_att.clock_out if today_att else None,
            "status": today_att.status if today_att else "absent",
            "total_hours": today_att.total_hours if today_att else None,
            "overtime_minutes": today_att.overtime_minutes if today_att else 0,
            "late_minutes": today_att.late_minutes if today_att else 0,
        },
        "month_attendance": {
            "total_days_present": sum(1 for a in month_att if a.status == "present"),
            "total_days_absent": sum(1 for a in month_att if a.status == "absent"),
            "total_days_late": sum(1 for a in month_att if a.status == "late"),
            "total_overtime_minutes": sum(a.overtime_minutes or 0 for a in month_att),
            "avg_hours": round(sum(a.total_hours or 0 for a in month_att) / max(len(month_att), 1), 2),
        },
        "salary": {
            "latest_payroll": {
                "id": latest_payroll.id if latest_payroll else None,
                "month": latest_payroll.payroll_month if latest_payroll else None,
                "year": latest_payroll.payroll_year if latest_payroll else None,
                "net_salary": float(latest_payroll.net_salary or 0) if latest_payroll else None,
                "status": latest_payroll.status if latest_payroll else None,
                "payslip_url": latest_payroll.payslip_url if latest_payroll else None,
            } if latest_payroll else None,
            "total_paid_this_year": float(sum(p.net_salary or 0 for p in payrolls)),
        },
        "leave": {
            "annual_entitlement": remaining_annual,
            "used_this_period": used_leaves,
            "remaining": max(remaining_annual - used_leaves, 0),
            "pending_requests": [
                {
                    "id": leave.id,
                    "leave_type": leave.leave_type,
                    "start_date": leave.start_date,
                    "end_date": leave.end_date,
                    "total_days": leave.total_days,
                    "reason": leave.reason,
                    "status": leave.status,
                }
                for leave in pending_leaves
            ],
        },
        "loans": {
            "pending_requests": [
                {
                    "id": loan.id,
                    "loan_type": loan.loan_type,
                    "amount": float(loan.amount),
                    "purpose": loan.purpose,
                    "monthly_installment": float(loan.monthly_installment or 0),
                    "status": loan.status,
                    "request_date": loan.request_date,
                }
                for loan in pending_loans
            ],
            "active_loans": [
                {
                    "id": loan.id,
                    "loan_type": loan.loan_type,
                    "amount": float(loan.amount),
                    "remaining_balance": float(loan.remaining_balance or 0),
                    "monthly_installment": float(loan.monthly_installment or 0),
                    "repayment_start": loan.repayment_start,
                    "repayment_end": loan.repayment_end,
                    "status": loan.status,
                }
                for loan in active_loans
            ],
        },
    }
