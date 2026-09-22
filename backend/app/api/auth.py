"""
The H.R - Auth API Router
Login, Register, Token Refresh, Profile
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_current_user,
    require_role,
)
from app.core.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    RegisterResponse,
    UserProfileResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
)
from app.models.models import User, Tenant, Employee, Department

router = APIRouter(prefix="/auth", tags=["Authentication"])


# -----------------------------------------------------------------------------
# Login
# -----------------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل الدخول - إرجاع JWT token"""
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="البريد الإلكتروني أو كلمة المرور غير صحيحة",
        )

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="البريد الإلكتروني أو كلمة المرور غير صحيحة",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="الحساب معطل",
        )

    # Update login info
    user.last_login = datetime.utcnow()
    user.failed_attempts = 0
    await db.commit()

    # Generate token
    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
        employee_id=str(user.employee.id) if user.employee else None,
        expires_delta=timedelta(minutes=1440),  # 24 hours
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=1440 * 60,
        user=UserResponse.model_validate(user),
    )


# -----------------------------------------------------------------------------
# Register (Super Admin Only)
# -----------------------------------------------------------------------------
@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin")),
):
    """إنشاء مستخدم جديد"""
    # Check tenant
    tenant = None
    if request.tenant_id:
        result = await db.execute(select(Tenant).where(Tenant.id == request.tenant_id))
        tenant = result.scalar_one_or_none()
    elif request.tenant_slug:
        result = await db.execute(select(Tenant).where(Tenant.slug == request.tenant_slug))
        tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="المؤسسة غير موجودة",
        )

    # Check email exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="البريد الإلكتروني مسجل مسبقاً",
        )

    # Create user
    password_hash = hash_password(request.password)
    new_user = User(
        email=request.email,
        password_hash=password_hash,
        full_name=request.full_name,
        phone=request.phone,
        role=request.role,
        tenant_id=tenant.id,
        is_active=True,
        is_verified=True,
    )
    db.add(new_user)
    await db.flush()

    employee = None
    if request.role == "employee" and (request.first_name or request.last_name):
        employee_number = f"EMP-{tenant.id.hex[:6].upper()}-{new_user.id.hex[:6].upper()}"
        employee = Employee(
            id=new_user.id,
            tenant_id=tenant.id,
            user_id=new_user.id,
            employee_number=employee_number,
            first_name=request.first_name or "",
            last_name=request.last_name or "",
            email=request.email,
            phone=request.phone,
            hire_date=request.hire_date,
            department_id=request.department_id,
            job_title=request.job_title,
            status="active",
        )
        db.add(employee)
        tenant.employee_count += 1

    await db.commit()
    await db.refresh(new_user)

    # Generate token
    access_token = create_access_token(
        subject=str(new_user.id),
        tenant_id=str(new_user.tenant_id),
        role=new_user.role,
        employee_id=str(new_user.employee.id) if new_user.employee else None,
        expires_delta=timedelta(minutes=1440),
    )

    return RegisterResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
        employee=EmployeeResponse.model_validate(employee) if employee else None,
    )


# -----------------------------------------------------------------------------
# Get Current User Profile
# -----------------------------------------------------------------------------
@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على بيانات المستخدم الحالي"""
    current_user = await get_current_user(credentials, db)
    user = current_user["user"]

    response_data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role,
        "employee_id": None,
        "employee_number": None,
        "department": None,
        "job_title": None,
        "hire_date": None,
        "avatar_url": None,
    }

    if user.employee:
        emp = user.employee
        response_data["employee_id"] = emp.id
        response_data["employee_number"] = emp.employee_number
        response_data["job_title"] = emp.job_title
        response_data["hire_date"] = emp.hire_date
        response_data["avatar_url"] = emp.avatar_url
        if emp.department:
            response_data["department"] = {
                "id": emp.department.id,
                "name": emp.department.name,
                "code": emp.department.code,
            }

    return UserProfileResponse(**response_data)


# -----------------------------------------------------------------------------
# Update Profile
# -----------------------------------------------------------------------------
@router.put("/me", response_model=UserProfileResponse)
async def update_profile(
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """تحديث بيانات المستخدم"""
    user = current_user["user"]

    if full_name:
        user.full_name = full_name
    if phone:
        user.phone = phone

    await db.commit()
    await db.refresh(user)

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
    )


# -----------------------------------------------------------------------------
# Change Password
# -----------------------------------------------------------------------------
@router.put("/password")
async def change_password(
    request: ChangePasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """تغيير كلمة المرور"""
    current_user = await get_current_user(credentials, db)
    user = current_user["user"]

    if not verify_password(request.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="كلمة المرور الحالية غير صحيحة",
        )

    user.password_hash = hash_password(request.new_password)
    await db.commit()

    return {"message": "تم تغيير كلمة المرور بنجاح"}


# -----------------------------------------------------------------------------
# Forgot Password
# -----------------------------------------------------------------------------
@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """طلب إعادة تعيين كلمة المرور"""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user:
        # Always return success to prevent email enumeration
        return {"message": "إذا كان البريد مسجلاً将是، ستصلك تعليمات إعادة التعيين"}

    # Generate reset token (in production, store in DB with expiration)
    reset_token = create_access_token(
        subject=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
        expires_delta=timedelta(hours=1),
    )

    # In production: send email with reset link
    # For now, return the token (should be sent via email)
    return {
        "message": "إذا كان البريد مسجلاً，将是Stories التعليمات لإعادة التعيين",
        # "reset_token": reset_token,  # Only for testing
    }
