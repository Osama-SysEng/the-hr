"""
The H.R - Payroll API Router
Payroll calculation, payslips, salary history
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import (
    Payroll, Employee, Tenant, AttendanceRecord, Department
)
import uuid


router = APIRouter(prefix="/payroll", tags=["Payroll"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from decimal import Decimal as PyDecimal


class PayrollCalculationRequest(BaseModel):
    employee_id: str
    payroll_month: int
    payroll_year: int
    calculate_attendance: bool = True
    calculate_insurance: bool = True
    calculate_tax: bool = True


class PayrollRecordResponse(BaseModel):
    id: str
    employee_id: str
    employee_number: str
    employee_name: str
    department_name: Optional[str] = None
    payroll_month: int
    payroll_year: int
    period_start: date
    period_end: date
    base_salary: float
    housing_allowance: float
    transport_allowance: float
    meal_allowance: float
    phone_allowance: float
    other_allowances: float
    overtime_pay: float
    total_earnings: float
    absence_deduction: float
    late_deduction: float
    violation_deduction: float
    loan_repayment: float
    other_deductions: float
    total_deductions: float
    social_insurance_employee: float
    social_insurance_employer: float
    health_insurance: float
    taxable_income: float
    income_tax: float
    net_salary: float
    status: str
    is_sent_to_employee: bool
    payslip_url: Optional[str] = None
    calculated_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PayrollListResponse(BaseModel):
    payrolls: List[PayrollRecordResponse]
    total: int
    page: int
    page_size: int


class PayslipResponse(BaseModel):
    employee_id: str
    employee_name: str
    employee_number: str
    payroll_month: int
    payroll_year: int
    period_start: date
    period_end: date
    base_salary: float
    allowances: dict
    deductions: dict
    insurance: dict
    tax: dict
    net_salary: float
    calculated_at: datetime
    notes: Optional[str] = None


class PayrollReportRequest(BaseModel):
    start_month: int
    start_year: int
    end_month: int
    end_year: int
    department_id: Optional[str] = None


class PayrollReportResponse(BaseModel):
    start_period: str
    end_period: str
    total_employees: int
    total_payroll_cost: float
    average_salary: float
    by_department: List[dict]
    by_month: List[dict]


# -----------------------------------------------------------------------------
# Helper: Calculate Egyptian Social Insurance
# -----------------------------------------------------------------------------
def calculate_social_insurance(salary: float) -> tuple:
    """
    Calculate Egyptian social insurance contributions.
    Employee: 11% of (salary - 720) up to max base
    Employer: 18.75% of (salary - 720) up to max base
    Minimum wage in Egypt (2024): 3,500 EGP
    Maximum insurance base: 9,800 EGP (subject to change)
    """
    min_wage = 3500
    max_base = 9800
    adjusted_salary = max(salary, min_wage)
    base = min(adjusted_salary, max_base)
    employee_portion = (base - 720) * 0.11 if base > 720 else 0
    employer_portion = (base - 720) * 0.1875 if base > 720 else 0
    return (
        round(max(employee_portion, 0), 2),
        round(max(employer_portion, 0), 2),
    )


# -----------------------------------------------------------------------------
# Helper: Calculate Egyptian Income Tax (2024 brackets)
# -----------------------------------------------------------------------------
def calculate_income_tax(annual_income: float) -> float:
    """
    Egyptian income tax brackets (2024).
    Annual income after deductions.
    """
    tax = 0
    remaining = annual_income

    # Bracket 1: 0 - 15,000 (0%)
    bracket_1 = min(remaining, 15000)
    remaining -= bracket_1

    # Bracket 2: 15,000 - 30,000 (10%)
    bracket_2 = min(remaining, 15000)
    tax += bracket_2 * 0.10
    remaining -= bracket_2

    # Bracket 3: 30,000 - 45,000 (15%)
    bracket_3 = min(remaining, 15000)
    tax += bracket_3 * 0.15
    remaining -= bracket_3

    # Bracket 4: 45,000 - 60,000 (20%)
    bracket_4 = min(remaining, 15000)
    tax += bracket_4 * 0.20
    remaining -= bracket_4

    # Bracket 5: 60,000 - 200,000 (22.5%)
    bracket_5 = min(remaining, 140000)
    tax += bracket_5 * 0.225
    remaining -= bracket_5

    # Bracket 6: > 200,000 (25%)
    tax += remaining * 0.25

    return round(tax, 2)


# -----------------------------------------------------------------------------
# Helper: Build payroll response
# -----------------------------------------------------------------------------
def _build_payroll_response(payroll: Payroll, employee: Employee, department: Optional[Department]) -> PayrollRecordResponse:
    return PayrollRecordResponse(
        id=payroll.id,
        employee_id=payroll.employee_id,
        employee_number=employee.employee_number,
        employee_name=f"{employee.first_name} {employee.last_name}",
        department_name=department.name if department else None,
        payroll_month=payroll.payroll_month,
        payroll_year=payroll.payroll_year,
        period_start=payroll.period_start,
        period_end=payroll.period_end,
        base_salary=float(payroll.base_salary or 0),
        housing_allowance=float(payroll.housing_allowance or 0),
        transport_allowance=float(payroll.transport_allowance or 0),
        meal_allowance=float(payroll.meal_allowance or 0),
        phone_allowance=float(payroll.phone_allowance or 0),
        other_allowances=float(payroll.other_allowances or 0),
        overtime_pay=float(payroll.overtime_pay or 0),
        total_earnings=float(payroll.total_earnings or 0),
        absence_deduction=float(payroll.absence_deduction or 0),
        late_deduction=float(payroll.late_deduction or 0),
        violation_deduction=float(payroll.violation_deduction or 0),
        loan_repayment=float(payroll.loan_repayment or 0),
        other_deductions=float(payroll.other_deductions or 0),
        total_deductions=float(payroll.total_deductions or 0),
        social_insurance_employee=float(payroll.social_insurance_employee or 0),
        social_insurance_employer=float(payroll.social_insurance_employer or 0),
        health_insurance=float(payroll.health_insurance or 0),
        taxable_income=float(payroll.taxable_income or 0),
        income_tax=float(payroll.income_tax or 0),
        net_salary=float(payroll.net_salary or 0),
        status=payroll.status,
        is_sent_to_employee=payroll.is_sent_to_employee,
        payslip_url=payroll.payslip_url,
        calculated_at=payroll.calculated_at,
        created_at=payroll.created_at,
    )


# -----------------------------------------------------------------------------
# Calculate Payroll
# -----------------------------------------------------------------------------
@router.post("/calculate", response_model=PayrollRecordResponse, status_code=status.HTTP_201_CREATED)
async def calculate_payroll(
    request: PayrollCalculationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager", "accountant")),
):
    """حساب راتب الموظف لشهر محدد"""
    tenant_id = current_user["tenant_id"]

    # Get employee
    emp_result = await db.execute(
        select(Employee)
        .where(Employee.id == request.employee_id)
        .where(Employee.tenant_id == tenant_id)
        .options(
            select.inload(Employee.department),
        )
    )
    employee = emp_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الموظف غير موجود",
        )

    # Check if payroll already exists
    existing_result = await db.execute(
        select(Payroll).where(
            and_(
                Payroll.employee_id == request.employee_id,
                Payroll.payroll_month == request.payroll_month,
                Payroll.payroll_year == request.payroll_year,
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="الراتب لهذا الشهر уже 계산되며",
        )

    # Base salary
    base_salary = employee.salary_base or Decimal("5000")

    # Allowances
    housing_allowance = Decimal("0")
    transport_allowance = Decimal("0")
    meal_allowance = Decimal("0")
    phone_allowance = Decimal("0")
    other_allowances = Decimal("0")

    # Get attendance for the period
    attendance_summaries = {}
    if request.calculate_attendance:
        start_date = date(request.payroll_year, request.payroll_month, 1)
        if request.payroll_month == 12:
            end_date = date(request.payroll_year, 12, 31)
        else:
            end_date = date(request.payroll_year, request.payroll_month + 1, 1) - timedelta(days=1)

        att_result = await db.execute(
            select(
                AttendanceRecord.date,
                AttendanceRecord.status,
                AttendanceRecord.total_hours,
                AttendanceRecord.overtime_minutes,
                AttendanceRecord.late_minutes,
                AttendanceRecord.early_departure_minutes,
            ).where(
                and_(
                    AttendanceRecord.employee_id == request.employee_id,
                    AttendanceRecord.tenant_id == tenant_id,
                    AttendanceRecord.date >= start_date,
                    AttendanceRecord.date <= end_date,
                )
            )
        )
        attendance_records = att_result.scalars().all()

        total_days = 0
        present_days = 0
        absent_days = 0
        late_days = 0
        total_hours_worked = 0
        total_overtime_minutes = 0
        total_late_minutes = 0

        for att in attendance_records:
            total_days += 1
            if att.status == "present":
                present_days += 1
                total_hours_worked += (att.total_hours or 0)
                total_overtime_minutes += att.overtime_minutes or 0
                total_late_minutes += att.late_minutes or 0
            elif att.status == "late":
                late_days += 1
                present_days += 1
            elif att.status == "absent":
                absent_days += 1

        # Absence deduction (per day rate)
        daily_rate = base_salary / 30
        absence_deduction = Decimal(str(daily_rate * absent_days))

        # Late deduction (5 EGP per late incident)
        late_deduction = Decimal(str(late_days * 5))

        # Overtime pay (30 EGP per hour)
        overtime_pay = Decimal(str((total_overtime_minutes / 60) * 30))

        # Housing allowance (typically 25% of base)
        housing_allowance = base_salary * Decimal("0.25")
        # Transport allowance (typically 10% of base)
        transport_allowance = base_salary * Decimal("0.10")
        # Meal allowance (typically 5% of base)
        meal_allowance = base_salary * Decimal("0.05")

    # Total earnings
    total_earnings = (
        base_salary +
        housing_allowance +
        transport_allowance +
        meal_allowance +
        phone_allowance +
        other_allowances +
        overtime_pay
    )

    # Total deductions
    total_deductions = (
        absence_deduction +
        late_deduction +
        Decimal("0")  # violation_deduction
        + Decimal("0")  # loan_repayment - would come from EmployeeLoan
        + Decimal("0")  # other_deductions
    )

    # Social insurance
    employee_insurance, employer_insurance = calculate_social_insurance(float(base_salary))

    # Health insurance (typically 1% of salary)
    health_insurance = base_salary * Decimal("0.01")

    # Taxable income
    taxable_income = total_earnings - employee_insurance - health_insurance
    annual_income = float(taxable_income) * 12
    income_tax = Decimal(str(calculate_income_tax(annual_income) / 12))

    # Net salary
    net_salary = total_earnings - total_deductions - employee_insurance - health_insurance - income_tax

    # Create payroll record
    period_start = date(request.payroll_year, request.payroll_month, 1)
    if request.payroll_month == 12:
        period_end = date(request.payroll_year, 12, 31)
    else:
        period_end = date(request.payroll_year, request.payroll_month + 1, 1) - timedelta(days=1)

    payroll = Payroll(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        employee_id=request.employee_id,
        payroll_month=request.payroll_month,
        payroll_year=request.payroll_year,
        period_start=period_start,
        period_end=period_end,
        base_salary=base_salary,
        housing_allowance=housing_allowance,
        transport_allowance=transport_allowance,
        meal_allowance=meal_allowance,
        phone_allowance=phone_allowance,
        other_allowances=other_allowances,
        overtime_pay=overtime_pay,
        total_earnings=total_earnings,
        absence_deduction=absence_deduction,
        late_deduction=late_deduction,
        violation_deduction=Decimal("0"),
        loan_repayment=Decimal("0"),
        other_deductions=Decimal("0"),
        total_deductions=total_deductions,
        social_insurance_employee=Decimal(str(employee_insurance)),
        social_insurance_employer=Decimal(str(employer_insurance)),
        health_insurance=health_insurance,
        taxable_income=taxable_income,
        income_tax=income_tax,
        net_salary=net_salary,
        status="calculated",
        calculated_at=datetime.now(timezone.utc),
    )
    db.add(payroll)
    await db.commit()
    await db.refresh(payroll)

    return _build_payroll_response(payroll, employee, employee.department)


# -----------------------------------------------------------------------------
# Get Payroll by ID
# -----------------------------------------------------------------------------
@router.get("/{payroll_id}", response_model=PayrollRecordResponse)
async def get_payroll(
    payroll_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """الحصول على سجل راتب محدد"""
    tenant_id = current_user["tenant_id"]
    role = current_user["role"]
    employee_id = current_user.get("employee_id")

    query = select(Payroll).where(
        and_(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
    ).options(
        select.inload(Payroll.employee),
        select.inload(Payroll.employee).selectinload(Employee.department),
    )

    # Non-admins can only see their own payroll
    if role not in ("super_admin", "company_admin", "hr_manager", "accountant"):
        if employee_id:
            query = query.where(Payroll.employee_id == employee_id)

    result = await db.execute(query)
    payroll = result.scalar_one_or_none()

    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سجل الراتب غير موجود",
        )

    return _build_payroll_response(payroll, payroll.employee, payroll.employee.department)


# -----------------------------------------------------------------------------
# List Payrolls
# -----------------------------------------------------------------------------
@router.get("", response_model=PayrollListResponse)
async def list_payrolls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employee_id: Optional[str] = Query(None),
    payroll_month: Optional[int] = Query(None),
    payroll_year: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """قائمة سجلات الرواتب"""
    tenant_id = current_user["tenant_id"]
    role = current_user["role"]
    employee_id_filter = current_user.get("employee_id")

    query = select(Payroll).where(Payroll.tenant_id == tenant_id)

    # Non-admins only see their own
    if role not in ("super_admin", "company_admin", "hr_manager", "accountant"):
        if employee_id_filter:
            query = query.where(Payroll.employee_id == employee_id_filter)

    if employee_id:
        query = query.where(Payroll.employee_id == employee_id)
    if payroll_month:
        query = query.where(Payroll.payroll_month == payroll_month)
    if payroll_year:
        query = query.where(Payroll.payroll_year == payroll_year)
    if status:
        query = query.where(Payroll.status == status)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sort and paginate
    query = query.order_by(Payroll.payroll_year.desc(), Payroll.payroll_month.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(
        query.options(
            select.inload(Payroll.employee),
            select.inload(Payroll.employee).selectinload(Employee.department),
        )
    )
    payrolls = result.scalars().all()

    return PayrollListResponse(
        payrolls=[_build_payroll_response(p, p.employee, p.employee.department) for p in payrolls],
        total=total,
        page=page,
        page_size=page_size,
    )


# -----------------------------------------------------------------------------
# Approve Payroll
# -----------------------------------------------------------------------------
@router.post("/{payroll_id}/approve")
async def approve_payroll(
    payroll_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin")),
):
    """الموافقة على راتب للدفع"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Payroll).where(
            and_(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
        ).options(selectinload(Payroll.employee))
    )
    payroll = result.scalar_one_or_none()

    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سجل الراتب غير موجود",
        )

    if payroll.status != "calculated":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن الموافقة على راتب غير محسوب",
        )

    payroll.status = "approved"
    await db.commit()

    return {"message": "تمت الموافقة على الراتب بنجاح", "status": payroll.status}


# -----------------------------------------------------------------------------
# Mark as Paid
# -----------------------------------------------------------------------------
@router.post("/{payroll_id}/pay")
async def mark_as_paid(
    payroll_id: str,
    bank_reference: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "accountant")),
):
    """تسجيل دفع الراتب"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Payroll).where(
            and_(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
        )
    )
    payroll = result.scalar_one_or_none()

    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سجل الراتب غير موجود",
        )

    if payroll.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يجب الموافقة على الراتب أولاً قبل الدفع",
        )

    payroll.status = "paid"
    if bank_reference:
        payroll.bank_reference = bank_reference
    payroll.is_sent_to_employee = True
    await db.commit()

    return {
        "message": "تم تسجيل دفع الراتب بنجاح",
        "status": payroll.status,
        "bank_reference": payroll.bank_reference,
    }


# -----------------------------------------------------------------------------
# Send Payslip to Employee
# -----------------------------------------------------------------------------
@router.post("/{payroll_id}/send")
async def send_payslip(
    payroll_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """إرسال كشف الراتب للموظف"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Payroll).where(
            and_(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
        )
    )
    payroll = result.scalar_one_or_none()

    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سجل الراتب غير موجود",
        )

    payroll.is_sent_to_employee = True
    await db.commit()

    return {
        "message": "تم إرسال كشف الراتب للموظف",
        "is_sent_to_employee": payroll.is_sent_to_employee,
    }


# -----------------------------------------------------------------------------
# Get Payslip PDF Data
# -----------------------------------------------------------------------------
@router.get("/{payroll_id}/payslip", response_model=PayslipResponse)
async def get_payslip_data(
    payroll_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """الحصول على بيانات كشف الراتب (للطباعة أو الإرسال)"""
    tenant_id = current_user["tenant_id"]
    role = current_user["role"]
    employee_id = current_user.get("employee_id")

    query = select(Payroll).where(
        and_(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
    ).options(selectinload(Payroll.employee))

    # Non-admins only see their own
    if role not in ("super_admin", "company_admin", "hr_manager", "accountant"):
        if employee_id:
            query = query.where(Payroll.employee_id == employee_id)

    result = await db.execute(query)
    payroll = result.scalar_one_or_none()

    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سجل الراتب غير موجود",
        )

    return PayslipResponse(
        employee_id=payroll.employee_id,
        employee_name=f"{payroll.employee.first_name} {payroll.employee.last_name}",
        employee_number=payroll.employee.employee_number,
        payroll_month=payroll.payroll_month,
        payroll_year=payroll.payroll_year,
        period_start=payroll.period_start,
        period_end=payroll.period_end,
        base_salary=float(payroll.base_salary or 0),
        allowances={
            "housing": float(payroll.housing_allowance or 0),
            "transport": float(payroll.transport_allowance or 0),
            "meal": float(payroll.meal_allowance or 0),
            "phone": float(payroll.phone_allowance or 0),
            "overtime": float(payroll.overtime_pay or 0),
            "other": float(payroll.other_allowances or 0),
        },
        deductions={
            "absence": float(payroll.absence_deduction or 0),
            "late": float(payroll.late_deduction or 0),
            "loan": float(payroll.loan_repayment or 0),
            "other": float(payroll.other_deductions or 0),
        },
        insurance={
            "social_employee": float(payroll.social_insurance_employee or 0),
            "social_employer": float(payroll.social_insurance_employer or 0),
            "health": float(payroll.health_insurance or 0),
        },
        tax={
            "taxable_income": float(payroll.taxable_income or 0),
            "income_tax": float(payroll.income_tax or 0),
        },
        net_salary=float(payroll.net_salary or 0),
        calculated_at=payroll.calculated_at,
        notes=payroll.notes,
    )


# -----------------------------------------------------------------------------
# Bulk Calculate Payroll for All Employees
# -----------------------------------------------------------------------------
@router.post("/calculate-all")
async def calculate_all_payrolls(
    payroll_month: int = Query(..., ge=1, le=12),
    payroll_year: int = Query(..., ge=2020, le=2100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager", "accountant")),
):
    """حساب رواتب جميع الموظفين لشهر محدد"""
    tenant_id = current_user["tenant_id"]

    # Get all active employees
    emp_result = await db.execute(
        select(Employee).where(
            and_(
                Employee.tenant_id == tenant_id,
                Employee.status == "active",
            )
        )
    )
    employees = emp_result.scalars().all()

    created = []
    for employee in employees:
        try:
            # Check if already exists
            existing_result = await db.execute(
                select(Payroll).where(
                    and_(
                        Payroll.employee_id == employee.id,
                        Payroll.payroll_month == payroll_month,
                        Payroll.payroll_year == payroll_year,
                    )
                )
            )
            if existing_result.scalar_one_or_none():
                continue

            # Calculate using the same logic as calculate_payroll
            # (simplified - would need to call the calculate logic)
            base_salary = employee.salary_base or Decimal("5000")

            payroll = Payroll(
                id=uuid.uuid4().hex,
                tenant_id=tenant_id,
                employee_id=employee.id,
                payroll_month=payroll_month,
                payroll_year=payroll_year,
                period_start=date(payroll_year, payroll_month, 1),
                period_end=date(payroll_year, payroll_month, 1) + timedelta(days=30),
                base_salary=base_salary,
                housing_allowance=base_salary * Decimal("0.25"),
                transport_allowance=base_salary * Decimal("0.10"),
                meal_allowance=base_salary * Decimal("0.05"),
                total_earnings=base_salary * Decimal("1.40"),
                total_deductions=Decimal("0"),
                social_insurance_employee=Decimal(str(round(base_salary * 0.11, 2))),
                social_insurance_employer=Decimal(str(round(base_salary * 0.1875, 2))),
                health_insurance=base_salary * Decimal("0.01"),
                net_salary=base_salary * Decimal("1.40") - base_salary * Decimal("0.11") - base_salary * Decimal("0.01"),
                status="calculated",
                calculated_at=datetime.now(timezone.utc),
            )
            db.add(payroll)
            created.append(payroll)

        except Exception:
            continue

    await db.commit()

    return {
        "message": f"تم حساب رواتب {len(created)} موظف",
        "created": len(created),
    }


# -----------------------------------------------------------------------------
# Get Payroll Statistics
# -----------------------------------------------------------------------------
@router.get("/statistics")
async def payroll_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager", "accountant")),
):
    """إحصائيات الرواتب"""
    tenant_id = current_user["tenant_id"]

    # Total payroll for current month
    current_month = datetime.now().month
    current_year = datetime.now().year

    result = await db.execute(
        select(
            func.count(Payroll.id).label("count"),
            func.sum(Payroll.net_salary).label("total_net"),
            func.avg(Payroll.net_salary).label("avg_net"),
            func.sum(Payroll.base_salary).label("total_base"),
        ).where(
            and_(
                Payroll.tenant_id == tenant_id,
                Payroll.payroll_month == current_month,
                Payroll.payroll_year == current_year,
            )
        )
    )
    stats = result.one()

    return {
        "current_month": current_month,
        "current_year": current_year,
        "total_employees_processed": stats.count or 0,
        "total_payroll_cost": float(stats.total_net or 0),
        "average_salary": float(stats.avg_net or 0),
        "total_base_salaries": float(stats.total_base or 0),
    }
