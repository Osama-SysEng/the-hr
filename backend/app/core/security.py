"""
The H.R - Security Module
JWT Authentication + RBAC + Password Hashing
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings


# -----------------------------------------------------------------------------
# Password Hashing
# -----------------------------------------------------------------------------
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# -----------------------------------------------------------------------------
# JWT Token Management
# -----------------------------------------------------------------------------
def create_access_token(
    subject: str,
    tenant_id: str,
    role: str,
    employee_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    
    Includes: user_id, tenant_id (multi-tenancy), role, employee_id
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    to_encode = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "employee_id": employee_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# -----------------------------------------------------------------------------
# Role-Based Access Control
# -----------------------------------------------------------------------------
ROLE_PERMISSIONS = {
    "super_admin": {
        "tenants:read", "tenants:write",
        "users:read", "users:write", "users:delete",
        "employees:read", "employees:write", "employees:delete",
        "attendance:read", "attendance:write",
        "payroll:read", "payroll:write",
        "recruitment:read", "recruitment:write",
        "supply_chain:read", "supply_chain:write",
        "analytics:read", "analytics:write",
        "settings:read", "settings:write",
        "audit:read",
    },
    "company_admin": {
        "employees:read", "employees:write", "employees:delete",
        "attendance:read", "attendance:write",
        "payroll:read", "payroll:write",
        "recruitment:read", "recruitment:write",
        "supply_chain:read", "supply_chain:write",
        "analytics:read", "analytics:write",
        "users:read",
        "settings:read", "settings:write",
    },
    "hr_manager": {
        "employees:read", "employees:write",
        "attendance:read", "attendance:write",
        "payroll:read",
        "recruitment:read", "recruitment:write",
        "analytics:read",
    },
    "manager": {
        "employees:read",  # own department
        "attendance:read",  # own department
        "payroll:read",  # own department
        "recruitment:read",
    },
    "employee": {
        "employees:read",  # own data
        "attendance:read",  # own data
        "payroll:read",  # own data
        "payroll:write",  # own leave requests
    },
    "accountant": {
        "payroll:read", "payroll:write",
        "employees:read",
    },
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Decode token and return user context."""
    payload = decode_access_token(credentials.credentials)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return {
        "user": user,
        "user_id": user_id,
        "tenant_id": payload.get("tenant_id"),
        "role": payload.get("role"),
        "employee_id": payload.get("employee_id"),
    }


def require_role(*allowed_roles: str):
    """Dependency factory: only allow specific roles."""
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user['role']}' not allowed. Required: {allowed_roles}",
            )
        return current_user
    return checker


def require_permission(permission: str):
    """Dependency factory: check specific permission."""
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        role_perms = ROLE_PERMISSIONS.get(current_user["role"], set())
        if permission not in role_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return current_user
    return checker
