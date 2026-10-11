"""
The H.R - Auth Schemas (Pydantic)
Login, Register, Token models
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# -----------------------------------------------------------------------------
# Auth Requests
# -----------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str | None = None
    role: str = "employee"  # super_admin, company_admin, hr_manager, manager, employee, accountant
    tenant_id: str | None = None
    tenant_slug: str | None = None
    # Employee data (if role is employee)
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: datetime | None = None
    gender: str | None = None
    hire_date: datetime | None = None
    department_id: str | None = None
    job_title: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# -----------------------------------------------------------------------------
# Auth Responses
# -----------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 -- OAuth2 token type identifier, not a password
    expires_in: int
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None = None
    role: str
    is_active: bool
    is_verified: bool
    last_login: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 -- OAuth2 token type identifier, not a password
    user: UserResponse
    employee: dict | None = None


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None = None
    role: str
    employee_id: str | None = None
    employee_number: str | None = None
    department: dict | None = None
    job_title: str | None = None
    hire_date: datetime | None = None
    avatar_url: str | None = None

    class Config:
        from_attributes = True


# -----------------------------------------------------------------------------
# Tenant / Company
# -----------------------------------------------------------------------------
class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    phone: str | None = None
    address: str | None = None
    subscription_tier: str = "starter"  # starter, growth, enterprise


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    email: str
    phone: str | None = None
    address: str | None = None
    logo_url: str | None = None
    primary_color: str
    subscription_tier: str
    subscription_status: str
    employee_count: int
    max_employees: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TenantSettingsRequest(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    company_name: str | None = None
