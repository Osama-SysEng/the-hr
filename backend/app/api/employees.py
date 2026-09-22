"""
The H.R - Employees API Router
Full CRUD for employees with filtering and search
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.schemas import UserResponse
from app.models.models import (
    Employee, User, Tenant, Department, AttendanceRecord,
    Payroll, LeaveRequest
)

router = APIRouter(prefix="/employees", tags=["Employees"])


# -----------------------------------------------------------------------------
# Schemas (inline for now - can move to schemas.py later)
# -----------------------------------------------------------------------------
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional as Opt


class EmployeeCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    blood_type: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    emergency_phone: Optional[str] = None
    email: Optional[str] = None
    social_insurance_number: Optional[str] = None
    hire_date: Optional[date] = None
    probation_end: Optional[date] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    contract_type: str = "permanent"
    department_id: Optional[str] = None
    job_title: Optional[str] = None
    employment_type: str = "full_time"
    salary_base: Optional[float] = None
    notes: Optional[str] = None


class EmployeeUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    blood_type: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    emergency_phone: Optional[str] = None
    email: Optional[str] = None
    social_insurance_number: Optional[str] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    contract_type: Optional[str] = None
    department_id: Optional[str] = None
    job_title: Optional[str] = None
    employment_type: Optional[str] = None
    salary_base: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class EmployeeResponse(BaseModel):
    id: str
    employee_number: str
    national_id: Optional[str] = None
    first_name: str
    last_name: str
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    blood_type: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    emergency_phone: Optional[str] = None
    email: Optional[str] = None
    social_insurance_number: Optional[str] = None
    fingerprint_template: Optional[str] = None
    face_encoding: Optional[str] = None
    hire_date: Optional[date] = None
    probation_end: Optional[date] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    contract_type: str
    status: str
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    job_title: Optional[str] = None
    employment_type: str
    salary_base: Optional[float] = None
    currency: str
    avatar_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmployeeListResponse(BaseModel):
    employees: List[EmployeeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# -----------------------------------------------------------------------------
# Helper: Build employee response
# -----------------------------------------------------------------------------
def _build_employee_response(emp: Employee) -> EmployeeResponse:
    return EmployeeResponse(
        id=emp.id,
        employee_number=emp.employee_number,
        national_id=emp.national_id,
        first_name=emp.first_name,
        last_name=emp.last_name,
        father_name=emp.father_name,
        mother_name=emp.mother_name,
        full_name=f"{emp.first_name} {emp.last_name}",
        date_of_birth=emp.date_of_birth,
        gender=emp.gender,
        marital_status=emp.marital_status,
        nationality=emp.nationality,
        religion=emp.religion,
        blood_type=emp.blood_type,
        address=emp.address,
        phone=emp.phone,
        emergency_phone=emp.emergency_phone,
        email=emp.email,
        social_insurance_number=emp.social_insurance_number,
        fingerprint_template=emp.fingerprint_template.hex() if emp.fingerprint_template else None,
        face_encoding=emp.face_encoding.hex() if emp.face_encoding else None,
        hire_date=emp.hire_date,
        probation_end=emp.probation_end,
        contract_start=emp.contract_start,
        contract_end=emp.contract_end,
        contract_type=emp.contract_type,
        status=emp.status,
        department_id=emp.department_id,
        department_name=emp.department.name if emp.department else None,
        job_title=emp.job_title,
        employment_type=emp.employment_type,
        salary_base=float(emp.salary_base) if emp.salary_base else None,
        currency=emp.currency,
        avatar_url=emp.avatar_url,
        notes=emp.notes,
        created_at=emp.created_at,
        updated_at=emp.updated_at,
    )


# -----------------------------------------------------------------------------
# List Employees
# -----------------------------------------------------------------------------
@router.get("", response_model=EmployeeListResponse)
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    department_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("employee_number"),
    sort_order: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """قائمة الموظفين مع التصفية والبحث"""
    tenant_id = current_user["tenant_id"]

    # Base query
    query = select(Employee).where(Employee.tenant_id == tenant_id)

    # Filters
    if status:
        query = query.where(Employee.status == status)
    if department_id:
        query = query.where(Employee.department_id == department_id)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Employee.first_name.ilike(search_term),
                Employee.last_name.ilike(search_term),
                Employee.employee_number.ilike(search_term),
                Employee.email.ilike(search_term),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Sorting
    sort_column = getattr(Employee, sort_by, Employee.employee_number)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute
    result = await db.execute(query)
    employees = result.scalars().all()

    return EmployeeListResponse(
        employees=[_build_employee_response(emp) for emp in employees],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# -----------------------------------------------------------------------------
# Get Employee by ID
# -----------------------------------------------------------------------------
@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """الحصول على بيانات موظف محدد"""
    tenant_id = current_user["tenant_id"]
    role = current_user["role"]

    query = select(Employee).where(Employee.id == employee_id)

    # Non-admins can only see their own data
    if role not in ("super_admin", "company_admin", "hr_manager"):
        if current_user.get("employee_id") != employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية لرؤية بيانات هذا الموظف",
            )

    query = query.where(Employee.tenant_id == tenant_id)
    query = query.options(selectinload(Employee.department))

    result = await db.execute(query)
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الموظف غير موجود",
        )

    return _build_employee_response(employee)


# -----------------------------------------------------------------------------
# Create Employee
# -----------------------------------------------------------------------------
@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    request: EmployeeCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """إنشاء موظف جديد"""
    tenant_id = current_user["tenant_id"]

    # Generate employee number
    result = await db.execute(
        select(func.max(Employee.employee_number)).where(Employee.tenant_id == tenant_id)
    )
    max_num = result.scalar()
    max_num_int = int(max_num.split("-")[-1]) if max_num and "-" in max_num else 0
    employee_number = f"EMP-{tenant_id.hex[:6].upper()}-{str(max_num_int + 1).zfill(6).upper()}"

    # Create employee
    employee = Employee(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        employee_number=employee_number,
        first_name=request.first_name,
        last_name=request.last_name,
        father_name=request.father_name,
        mother_name=request.mother_name,
        date_of_birth=request.date_of_birth,
        gender=request.gender,
        marital_status=request.marital_status,
        nationality=request.nationality,
        religion=request.religion,
        blood_type=request.blood_type,
        address=request.address,
        phone=request.phone,
        emergency_phone=request.emergency_phone,
        email=request.email,
        social_insurance_number=request.social_insurance_number,
        hire_date=request.hire_date,
        probation_end=request.probation_end,
        contract_start=request.contract_start,
        contract_end=request.contract_end,
        contract_type=request.contract_type,
        department_id=request.department_id,
        job_title=request.job_title,
        employment_type=request.employment_type,
        salary_base=request.salary_base,
        notes=request.notes,
        status="active",
        currency="EGP",
    )

    db.add(employee)
    await db.flush()

    # Update tenant employee count
    tenant = await db.get(Tenant, tenant_id)
    if tenant:
        tenant.employee_count += 1

    await db.commit()
    await db.refresh(employee)

    # Load department
    await db.execute(
        select(Department).where(Department.id == employee.department_id)
    )

    return _build_employee_response(employee)


# -----------------------------------------------------------------------------
# Update Employee
# -----------------------------------------------------------------------------
@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: str,
    request: EmployeeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """تحديث بيانات موظف"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Employee)
        .where(Employee.id == employee_id)
        .where(Employee.tenant_id == tenant_id)
        .options(selectinload(Employee.department))
    )
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الموظف غير موجود",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    await db.commit()
    await db.refresh(employee)

    return _build_employee_response(employee)


# -----------------------------------------------------------------------------
# Delete Employee (Soft Delete - Set status to terminated)
# -----------------------------------------------------------------------------
@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin")),
):
    """إتمام خدمة موظف (soft delete)"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Employee).where(Employee.id == employee_id).where(Employee.tenant_id == tenant_id)
    )
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الموظف غير موجود",
        )

    employee.status = "terminated"
    employee.terminated_at = datetime.utcnow()
    await db.commit()


# -----------------------------------------------------------------------------
# Bulk Import
# -----------------------------------------------------------------------------
@router.post("/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_import_employees(
    employees_data: List[EmployeeCreateRequest],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """استيراد دفعة من الموظفين"""
    tenant_id = current_user["tenant_id"]
    created = []

    for emp_data in employees_data:
        employee_number = f"EMP-{tenant_id.hex[:6].upper()}-{uuid.uuid4().hex[:6].upper()}"
        employee = Employee(
            id=uuid.uuid4().hex,
            tenant_id=tenant_id,
            employee_number=employee_number,
            **emp_data.model_dump(),
            status="active",
            currency="EGP",
        )
        db.add(employee)
        created.append(employee)

    await db.flush()

    # Update tenant count
    tenant = await db.get(Tenant, tenant_id)
    if tenant:
        tenant.employee_count += len(created)

    await db.commit()

    return {
        "created": len(created),
        "employees": [_build_employee_response(emp) for emp in created],
    }


# -----------------------------------------------------------------------------
# Search Employees (Autocomplete)
# -----------------------------------------------------------------------------
@router.get("/search")
async def search_employees(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """بحث سريع عن الموظفين (للاستخدام في الـ autocomplete)"""
    tenant_id = current_user["tenant_id"]

    search_term = f"%{q}%"
    result = await db.execute(
        select(Employee)
        .where(Employee.tenant_id == tenant_id)
        .where(
            or_(
                Employee.first_name.ilike(search_term),
                Employee.last_name.ilike(search_term),
                Employee.employee_number.ilike(search_term),
            )
        )
        .order_by(Employee.first_name)
        .limit(limit)
    )
    employees = result.scalars().all()

    return {
        "results": [
            {
                "id": emp.id,
                "label": f"{emp.first_name} {emp.last_name} ({emp.employee_number})",
                "value": emp.id,
            }
            for emp in employees
        ]
    }
