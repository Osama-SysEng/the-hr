"""
The H.R - Auth Schemas (Pydantic)
Login, Register, Token models
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# -----------------------------------------------------------------------------
# Auth Requests
# -----------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: Optional[str] = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    role: str = "employee"  # super_admin, company_admin, hr_manager, manager, employee, accountant
    tenant_id: Optional[str] = None
    tenant_slug: Optional[str] = None
    # Employee data (if role is employee)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    hire_date: Optional[datetime] = None
    department_id: Optional[str] = None
    job_title: Optional[str] = None


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
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    employee: Optional[dict] = None


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    employee_id: Optional[str] = None
    employee_number: Optional[str] = None
    department: Optional[dict] = None
    job_title: Optional[str] = None
    hire_date: Optional[datetime] = None
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True


# -----------------------------------------------------------------------------
# Tenant / Company
# -----------------------------------------------------------------------------
class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    subscription_tier: str = "starter"  # starter, growth, enterprise


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
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
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    company_name: Optional[str] = None
