"""
The H.R - Leave & Loans API Router
Leave management, employee loans/advance
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import (
    LeaveRequest, EmployeeLoan, Employee, Tenant, Department
)
import uuid


router = APIRouter(prefix="/hr", tags=["Leave & Loans"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


class LeaveRequestCreate(BaseModel):
    leave_type: str = Field(..., min_length=1, max_length=50)
    start_date: date
    end_date: date
    reason: Optional[str] = None
    attachment_url: Optional[str] = None


class LeaveRequestResponse(BaseModel):
    id: str
    employee_id: str
    employee_name: str
    employee_number: str
    department_name: Optional[str] = None
    leave_type: str
    start_date: date
    end_date: date
    total_days: int
    reason: Optional[str] = None
    status: str
    attachment_url: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LeaveListResponse(BaseModel):
    leaves: List[LeaveRequestResponse]
    total: int
    page: int
    page_size: int


class LeaveBalanceResponse(BaseModel):
    employee_id: str
    employee_name: str
    annual_balance: float
    sick_balance: float
    emergency_balance: float
    used_this_year: int
    total_entitlement: int


class LoanRequestCreate(BaseModel):
    loan_type: str = Field(..., min_length=1, max_length=50)
    amount: float = Field(..., gt=0)
    purpose: Optional[str] = None


class LoanResponse(BaseModel):
    id: str
    employee_id: str
    employee_name: str
    employee_number: str
    loan_type: str
    amount: float
    purpose: Optional[str] = None
    request_date: date
    repayment_start: date
    repayment_end: Optional[date] = None
    monthly_installment: float
    remaining_balance: float
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LoanListResponse(BaseModel):
    loans: List[LoanResponse]
    total: int
    page: int
    page_size: int


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------
def _build_leave_response(leave: LeaveRequest, employee: Employee, dept: Optional[Department]) -> LeaveRequestResponse:
    return LeaveRequestResponse(
        id=leave.id,
        employee_id=leave.employee_id,
        employee_name=f"{employee.first_name} {employee.last_name}",
        employee_number=employee.employee_number,
        department_name=dept.name if dept else None,
        leave_type=leave.leave_type,
        start_date=leave.start_date,
        end_date=leave.end_date,
        total_days=leave.total_days,
        reason=leave.reason,
        status=leave.status,
        attachment_url=leave.attachment_url,
        approved_by=leave.approved_by,
        approved_at=leave.approved_at,
        rejection_reason=leave.rejection_reason,
        created_at=leave.created_at,
    )


def _build_loan_response(loan: EmployeeLoan, employee: Employee) -> LoanResponse:
    return LoanResponse(
        id=loan.id,
        employee_id=loan.employee_id,
        employee_name=f"{employee.first_name} {employee.last_name}",
        employee_number=employee.employee_number,
        loan_type=loan.loan_type,
        amount=float(loan.amount),
        purpose=loan.purpose,
        request_date=loan.request_date,
        repayment_start=loan.repayment_start,
        repayment_end=loan.repayment_end,
        monthly_installment=float(loan.monthly_installment or 0),
        remaining_balance=float(loan.remaining_balance or 0),
        status=loan.status,
        approved_by=loan.approved_by,
        approved_at=loan.approved_at,
        created_at=loan.created_at,
    )


# -----------------------------------------------------------------------------
# Leave Requests
# -----------------------------------------------------------------------------
@router.get("/leaves", response_model=LeaveListResponse)
async def list_leaves(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """قائمة طلبات الإجازة"""
    tenant_id = current_user["tenant_id"]
    role = current_user["role"]
    emp_id = current_user.get("employee_id")

    query = select(LeaveRequest).where(LeaveRequest.tenant_id == tenant_id)

    # Non-admins only see their own
    if role not in ("super_admin", "company_admin", "hr_manager", "manager"):
        if emp_id:
            query = query.where(LeaveRequest.employee_id == emp_id)

    if status:
        query = query.where(LeaveRequest.status == status)
    if employee_id:
        query = query.where(LeaveRequest.employee_id == employee_id)
    if start_date:
        query = query.where(LeaveRequest.start_date >= start_date)
    if end_date:
        query = query.where(LeaveRequest.end_date <= end_date)

    query = query.order_by(LeaveRequest.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        query.options(
            selectinload(LeaveRequest.employee).selectinload(Employee.department),
        )
    )
    leaves = result.scalars().all()

    return LeaveListResponse(
        leaves=[_build_leave_response(l, l.employee, l.employee.department) for l in leaves],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/leaves", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_leave_request(
    request: LeaveRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """طلب إجازة جديدة"""
    tenant_id = current_user["tenant_id"]
    employee_id = current_user.get("employee_id")

    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يجب أن يكون لديك حساب موظف لطلب إجازة",
        )

    # Calculate total days
    total_days = (request.end_date - request.start_date).days + 1

    leave = LeaveRequest(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        employee_id=employee_id,
        leave_type=request.leave_type,
        start_date=request.start_date,
        end_date=request.end_date,
        total_days=total_days,
        reason=request.reason,
        attachment_url=request.attachment_url,
        status="pending",
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)

    emp_result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = emp_result.scalar_one_or_none()
    dept = employee.department if employee else None

    return _build_leave_response(leave, employee, dept)


@router.put("/leaves/{leave_id}/approve")
async def approve_leave(
    leave_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager", "manager")),
):
    """موافقة على طلب إجازة"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(LeaveRequest).where(
            and_(LeaveRequest.id == leave_id, LeaveRequest.tenant_id == tenant_id)
        ).options(selectinload(LeaveRequest.employee))
    )
    leave = result.scalar_one_or_none()

    if not leave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="طلب الإجازة غير موجود",
        )

    if leave.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="طلب الإجازة 상태이다 بالفعل",
        )

    leave.status = "approved"
    leave.approved_by = current_user["user_id"]
    leave.approved_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "تمت الموافقة على الإجازة", "status": leave.status}


@router.put("/leaves/{leave_id}/reject")
async def reject_leave(
    leave_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager", "manager")),
):
    """رفض طلب إجازة"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(LeaveRequest).where(
            and_(LeaveRequest.id == leave_id, LeaveRequest.tenant_id == tenant_id)
        )
    )
    leave = result.scalar_one_or_none()

    if not leave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="طلب الإجازة غير موجود",
        )

    if leave.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="طلب الإجازة 상태이다 بالفعل",
        )

    leave.status = "rejected"
    leave.approved_by = current_user["user_id"]
    leave.approved_at = datetime.now(timezone.utc)
    if reason:
        leave.rejection_reason = reason
    await db.commit()

    return {"message": "تم رفض طلب الإجازة", "status": leave.status}


@router.get("/leaves/balance")
async def get_leave_balance(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """رصيد الإجازات للموظف الحالي"""
    employee_id = current_user.get("employee_id")
    tenant_id = current_user["tenant_id"]

    if not employee_id:
        return {
            "message": "ليس لديك حساب موظف",
            "annual_balance": 0,
            "sick_balance": 0,
            "emergency_balance": 0,
        }

    # Get employee leave entitlement (based on service years)
    emp_result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = emp_result.scalar_one_or_none()

    if not employee:
        return {"message": "الموظف غير موجود"}

    # Calculate entitlement based on years of service
    if employee.hire_date:
        service_years = (date.today() - employee.hire_date).days / 365
        annual_entitlement = min(30, max(15, int(service_years * 25)))
    else:
        annual_entitlement = 21

    # Count used leaves this year
    current_year = date.today().year
    used_result = await db.execute(
        select(func.count(LeaveRequest.id)).where(
            and_(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.status == "approved",
                func.extract("year", LeaveRequest.start_date) == current_year,
            )
        )
    )
    used_this_year = used_result.scalar() or 0

    # Count by type
    sick_result = await db.execute(
        select(func.count(LeaveRequest.id)).where(
            and_(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.leave_type == "sick",
                LeaveRequest.status == "approved",
                func.extract("year", LeaveRequest.start_date) == current_year,
            )
        )
    )
    sick_used = sick_result.scalar() or 0

    emergency_result = await db.execute(
        select(func.count(LeaveRequest.id)).where(
            and_(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.leave_type == "emergency",
                LeaveRequest.status == "approved",
                func.extract("year", LeaveRequest.start_date) == current_year,
            )
        )
    )
    emergency_used = emergency_result.scalar() or 0

    return LeaveBalanceResponse(
        employee_id=employee_id,
        employee_name=f"{employee.first_name} {employee.last_name}",
        annual_balance=annual_entitlement - used_this_year,
        sick_balance=10 - sick_used,
        emergency_balance=2 - emergency_used,
        used_this_year=used_this_year,
        total_entitlement=annual_entitlement,
    )


# -----------------------------------------------------------------------------
# Employee Loans / Advances
# -----------------------------------------------------------------------------
@router.get("/loans", response_model=LoanListResponse)
async def list_loans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """قائمة قروض/تقديمات الموظفين"""
    tenant_id = current_user["tenant_id"]
    role = current_user["role"]
    emp_id = current_user.get("employee_id")

    query = select(EmployeeLoan).where(EmployeeLoan.tenant_id == tenant_id)

    # Non-admins only see their own
    if role not in ("super_admin", "company_admin", "hr_manager", "accountant"):
        if emp_id:
            query = query.where(EmployeeLoan.employee_id == emp_id)

    if status:
        query = query.where(EmployeeLoan.status == status)
    if employee_id:
        query = query.where(EmployeeLoan.employee_id == employee_id)

    query = query.order_by(EmployeeLoan.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        query.options(selectinload(EmployeeLoan.employee))
    )
    loans = result.scalars().all()

    return LoanListResponse(
        loans=[_build_loan_response(l, l.employee) for l in loans],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/loans", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def request_loan(
    request: LoanRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """طلب قرض/تقديم جديد"""
    tenant_id = current_user["tenant_id"]
    employee_id = current_user.get("employee_id")

    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يجب أن يكون لديك حساب موظف لطلب قرض",
        )

    emp_result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = emp_result.scalar_one_or_none()

    # Calculate repayment schedule
    if request.loan_type == "advance":
        monthly_installment = Decimal(str(request.amount / 3))  # 3 months
        repayment_end = date.today() + timedelta(days=90)
    elif request.loan_type == "loan":
        monthly_installment = Decimal(str(request.amount / 12))  # 12 months
        repayment_end = date.today() + timedelta(days=365)
    else:
        monthly_installment = Decimal(str(request.amount / 6))
        repayment_end = date.today() + timedelta(days=180)

    loan = EmployeeLoan(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        employee_id=employee_id,
        loan_type=request.loan_type,
        amount=Decimal(str(request.amount)),
        purpose=request.purpose,
        request_date=date.today(),
        repayment_start=date.today(),
        repayment_end=repayment_end,
        monthly_installment=monthly_installment,
        remaining_balance=Decimal(str(request.amount)),
        status="pending",
    )
    db.add(loan)
    await db.commit()
    await db.refresh(loan)

    return _build_loan_response(loan, employee)


@router.put("/loans/{loan_id}/approve")
async def approve_loan(
    loan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """موافقة على قرض"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(EmployeeLoan).where(
            and_(EmployeeLoan.id == loan_id, EmployeeLoan.tenant_id == tenant_id)
        )
    )
    loan = result.scalar_one_or_none()

    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="القرض غير موجود",
        )

    if loan.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="القرض состоянием بالفعل",
        )

    loan.status = "active"
    loan.approved_by = current_user["user_id"]
    loan.approved_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "تمت الموافقة على القرض", "status": loan.status}


@router.put("/loans/{loan_id}/reject")
async def reject_loan(
    loan_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """رفض قرض"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(EmployeeLoan).where(
            and_(EmployeeLoan.id == loan_id, EmployeeLoan.tenant_id == tenant_id)
        )
    )
    loan = result.scalar_one_or_none()

    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="القرض غير موجود",
        )

    if loan.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="القرض состоянием بالفعل",
        )

    loan.status = "rejected"
    loan.approved_by = current_user["user_id"]
    loan.approved_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "تم رفض القرض", "status": loan.status}
