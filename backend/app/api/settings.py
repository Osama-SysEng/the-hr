"""
The H.R - Dashboard & Settings API
Company settings, dashboard widgets
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import Tenant, Employee, User


router = APIRouter(prefix="/settings", tags=["Company Settings"])


# -----------------------------------------------------------------------------
# Company Settings
# -----------------------------------------------------------------------------
@router.get("/company")
async def get_company_settings(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """الحصول على إعدادات الشركة"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المؤسسة غير موجودة",
        )

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "email": tenant.email,
        "phone": tenant.phone,
        "address": tenant.address,
        "logo_url": tenant.logo_url,
        "primary_color": tenant.primary_color,
        "subscription_tier": tenant.subscription_tier,
        "subscription_status": tenant.subscription_status,
        "employee_count": tenant.employee_count,
        "max_employees": tenant.max_employees,
        "country": tenant.country,
        "currency": tenant.currency,
        "time_zone": tenant.time_zone,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at,
    }


@router.put("/company")
async def update_company_settings(
    name: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    logo_url: Optional[str] = None,
    primary_color: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin")),
):
    """تحديثإعدادات الشركة"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المؤسسة غير موجودة",
        )

    if name:
        tenant.name = name
    if phone:
        tenant.phone = phone
    if address:
        tenant.address = address
    if logo_url:
        tenant.logo_url = logo_url
    if primary_color:
        tenant.primary_color = primary_color

    await db.commit()
    await db.refresh(tenant)

    return {
        "message": "تم تحديث الإعدادات بنجاح",
        "company": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "email": tenant.email,
            "phone": tenant.phone,
            "address": tenant.address,
            "logo_url": tenant.logo_url,
            "primary_color": tenant.primary_color,
        },
    }


# -----------------------------------------------------------------------------
# Employee Quick Info (for dropdown/select)
# -----------------------------------------------------------------------------
@router.get("/employees/simple-list")
async def get_simple_employee_list(
    search: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """قائمة موظفين مبسطة (للاستخدام في الـ dropdown)"""
    tenant_id = current_user["tenant_id"]

    query = select(Employee).where(Employee.tenant_id == tenant_id)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Employee.first_name.ilike(search_term),
                Employee.last_name.ilike(search_term),
                Employee.employee_number.ilike(search_term),
            )
        )

    query = query.limit(limit)
    result = await db.execute(query)
    employees = result.scalars().all()

    return {
        "employees": [
            {
                "id": emp.id,
                "employee_number": emp.employee_number,
                "name": f"{emp.first_name} {emp.last_name}",
                "job_title": emp.job_title,
                "department_id": emp.department_id,
                "status": emp.status,
            }
            for emp in employees
        ]
    }


# -----------------------------------------------------------------------------
# Department List
# -----------------------------------------------------------------------------
@router.get("/departments")
async def list_departments(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """قائمة الأقسام"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Department).where(Department.tenant_id == tenant_id).order_by(Department.name)
    )
    departments = result.scalars().all()

    return {
        "departments": [
            {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "description": dept.description,
                "manager_id": dept.manager_id,
                "is_active": dept.is_active,
            }
            for dept in departments
        ]
    }


# -----------------------------------------------------------------------------
# User Profile (with employee info)
# -----------------------------------------------------------------------------
@router.get("/profile")
async def get_full_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """الملف الشخصي الكامل للمستخدم الحالي"""
    user = current_user["user"]
    employee = user.employee

    result = {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "last_login": user.last_login,
        }
    }

    if employee:
        result["employee"] = {
            "id": employee.id,
            "employee_number": employee.employee_number,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "national_id": employee.national_id,
            "date_of_birth": employee.date_of_birth,
            "gender": employee.gender,
            "marital_status": employee.marital_status,
            "address": employee.address,
            "phone": employee.phone,
            "email": employee.email,
            "social_insurance_number": employee.social_insurance_number,
            "hire_date": employee.hire_date,
            "contract_start": employee.contract_start,
            "contract_end": employee.contract_end,
            "contract_type": employee.contract_type,
            "status": employee.status,
            "department_id": employee.department_id,
            "job_title": employee.job_title,
            "employment_type": employee.employment_type,
            "salary_base": float(employee.salary_base) if employee.salary_base else None,
            "avatar_url": employee.avatar_url,
        }

        if employee.department:
            result["employee"]["department"] = {
                "id": employee.department.id,
                "name": employee.department.name,
                "code": employee.department.code,
            }

    return result
