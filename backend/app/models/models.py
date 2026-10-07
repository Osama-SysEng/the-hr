"""
The H.R - Database Models
SQLAlchemy ORM Models for all HR modules
"""

import uuid
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List
from enum import Enum as PyEnum
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Date, ForeignKey,
    Enum as SQLEnum, Text, Numeric, JSON, UniqueConstraint, Index, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from app.core.database import Base


# =============================================================================
# Enums
# =============================================================================
class UserRole(str, PyEnum):
    SUPER_ADMIN = "super_admin"
    COMPANY_ADMIN = "company_admin"
    HR_MANAGER = "hr_manager"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    ACCOUNTANT = "accountant"


class EmployeeStatus(str, PyEnum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"
    PROBATION = "probation"
    RETIRED = "retired"


class AttendanceStatus(str, PyEnum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    HALF_DAY = "half_day"
    ON_LEAVE = "on_leave"
    CLOCKED_IN = "clocked_in"
    CLOCKED_OUT = "clocked_out"


class LeaveType(str, PyEnum):
    ANNUAL = "annual"
    SICK = "sick"
    EMERGENCY = "emergency"
    UNPAID = "unpaid"
    MATERNITY = "maternity"
    PATERNITY = "paternity"


class LeaveStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PayrollStatus(str, PyEnum):
    DRAFT = "draft"
    CALCULATED = "calculated"
    APPROVED = "approved"
    PAID = "paid"


class RecruitmentStage(str, PyEnum):
    NEW = "new"
    SCREENING = "screening"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"


class Gender(str, PyEnum):
    MALE = "male"
    FEMALE = "female"


class EmploymentType(str, PyEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


# =============================================================================
# Tenant (Company)
# =============================================================================
class Tenant(Base, AsyncAttrs):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(Text)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    primary_color: Mapped[str] = mapped_column(String(7), default="#0d6efd")
    subscription_tier: Mapped[str] = mapped_column(String(50), default="starter")
    subscription_status: Mapped[str] = mapped_column(String(50), default="active")
    employee_count: Mapped[int] = mapped_column(Integer, default=0)
    max_employees: Mapped[int] = mapped_column(Integer, default=50)
    country: Mapped[Optional[str]] = mapped_column(String(100), default="EG")
    currency: Mapped[str] = mapped_column(String(3), default="EGP")
    time_zone: Mapped[str] = mapped_column(String(50), default="Africa/Cairo")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="tenant", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="tenant", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="tenant")
    payrolls = relationship("Payroll", back_populates="tenant")
    jobs = relationship("JobPosting", back_populates="tenant")
    candidates = relationship("Candidate", back_populates="tenant")
    inventory_products = relationship("InventoryProduct", back_populates="tenant")
    suppliers = relationship("Supplier", back_populates="tenant")

    __table_args__ = (
        Index("ix_tenant_slug", "slug"),
    )


# =============================================================================
# User (Authentication)
# =============================================================================
class User(Base, AsyncAttrs):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="employee")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))

    tenant = relationship("Tenant", back_populates="users")
    employee = relationship("Employee", back_populates="user", uselist=False)

    __table_args__ = (
        Index("ix_users_tenant_email", "tenant_id", "email"),
    )


# =============================================================================
# Department
# =============================================================================
class Department(Base, AsyncAttrs):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    manager_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"))
    parent_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    tenant = relationship("Tenant", back_populates="departments")
    manager = relationship("Employee", foreign_keys=[manager_id])
    employees = relationship("Employee", back_populates="department")
    parent = relationship("Department", remote_side=[id], back_populates="children")
    children = relationship("Department", back_populates="parent")

    __table_args__ = (
        Index("ix_departments_tenant", "tenant_id"),
        Index("ix_departments_code", "tenant_id", "code"),
    )


# =============================================================================
# Employee
# =============================================================================
class Employee(Base, AsyncAttrs):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    employee_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    national_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    father_name: Mapped[Optional[str]] = mapped_column(String(100))
    mother_name: Mapped[Optional[str]] = mapped_column(String(100))
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    marital_status: Mapped[Optional[str]] = mapped_column(String(20))
    nationality: Mapped[Optional[str]] = mapped_column(String(100))
    religion: Mapped[Optional[str]] = mapped_column(String(50))
    blood_type: Mapped[Optional[str]] = mapped_column(String(5))
    address: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    emergency_phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    social_insurance_number: Mapped[Optional[str]] = mapped_column(String(50))
    fingerprint_template: Mapped[Optional[bytes]] = mapped_column(Text)  # Base64 encoded
    face_encoding: Mapped[Optional[bytes]] = mapped_column(Text)  # Base64 encoded vector
    hire_date: Mapped[Optional[date]] = mapped_column(Date)
    probation_end: Mapped[Optional[date]] = mapped_column(Date)
    contract_start: Mapped[Optional[date]] = mapped_column(Date)
    contract_end: Mapped[Optional[date]] = mapped_column(Date)
    contract_type: Mapped[str] = mapped_column(String(50), default="permanent")
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    department_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), index=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(255))
    employment_type: Mapped[str] = mapped_column(String(50), default="full_time")
    salary_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EGP")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))
    terminated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    terminated_reason: Mapped[Optional[str]] = mapped_column(Text)

    tenant = relationship("Tenant", back_populates="employees")
    user = relationship("User", back_populates="employee")
    department = relationship("Department", back_populates="employees")
    attendance_records = relationship("AttendanceRecord", back_populates="employee")
    payrolls = relationship("Payroll", back_populates="employee")
    leave_requests = relationship("LeaveRequest", back_populates="employee")
    loans = relationship("EmployeeLoan", back_populates="employee")
    performance_reviews = relationship("PerformanceReview", back_populates="employee")

    __table_args__ = (
        Index("ix_employees_tenant_status", "tenant_id", "status"),
        Index("ix_employees_department", "department_id"),
    )


# =============================================================================
# Attendance Record
# =============================================================================
class AttendanceRecord(Base, AsyncAttrs):
    __tablename__ = "attendance_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    clock_in: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    clock_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="present")
    biometric_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    biometric_device_id: Mapped[Optional[str]] = mapped_column(String(100))
    gps_lat: Mapped[Optional[float]] = mapped_column(Float)
    gps_lng: Mapped[Optional[float]] = mapped_column(Float)
    gps_accuracy: Mapped[Optional[float]] = mapped_column(Float)
    gps_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    photo_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    face_match_score: Mapped[Optional[float]] = mapped_column(Float)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_departure_minutes: Mapped[int] = mapped_column(Integer, default=0)
    total_hours: Mapped[Optional[float]] = mapped_column(Float)
    overtime_minutes: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    verified_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))

    tenant = relationship("Tenant", back_populates="attendance_records")
    employee = relationship("Employee", back_populates="attendance_records")

    __table_args__ = (
        Index("ix_attendance_tenant_employee_date", "tenant_id", "employee_id", "date"),
        Index("ix_attendance_date", "date"),
    )


# =============================================================================
# Leave Request
# =============================================================================
class LeaveRequest(Base, AsyncAttrs):
    __tablename__ = "leave_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    attachment_url: Mapped[Optional[str]] = mapped_column(String(500))
    approved_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    employee = relationship("Employee", back_populates="leave_requests")

    __table_args__ = (
        Index("ix_leave_tenant_employee", "tenant_id", "employee_id"),
        Index("ix_leave_status", "status"),
    )


# =============================================================================
# Employee Loan / Advance
# =============================================================================
class EmployeeLoan(Base, AsyncAttrs):
    __tablename__ = "employee_loans"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    loan_type: Mapped[str] = mapped_column(String(50), nullable=False)  # advance, loan, salary_advance
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(String(255))
    request_date: Mapped[date] = mapped_column(Date, nullable=False)
    repayment_start: Mapped[date] = mapped_column(Date, nullable=False)
    repayment_end: Mapped[Optional[date]] = mapped_column(Date)
    monthly_installment: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    remaining_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, paid, cancelled
    approved_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    employee = relationship("Employee", back_populates="loans")

    __table_args__ = (
        Index("ix_loans_tenant_employee", "tenant_id", "employee_id"),
    )


# =============================================================================
# Payroll
# =============================================================================
class Payroll(Base, AsyncAttrs):
    __tablename__ = "payrolls"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    payroll_month: Mapped[int] = mapped_column(Integer, nullable=False)
    payroll_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Earnings
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    housing_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    transport_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    meal_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    phone_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    other_allowances: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    overtime_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # Deductions
    absence_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    late_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    violation_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    loan_repayment: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # Insurance
    social_insurance_employee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    social_insurance_employer: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    health_insurance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # Tax
    taxable_income: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    income_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # Net
    net_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    is_sent_to_employee: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bank_transfer: Mapped[bool] = mapped_column(Boolean, default=True)
    bank_reference: Mapped[Optional[str]] = mapped_column(String(255))
    payslip_url: Mapped[Optional[str]] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    tenant = relationship("Tenant", back_populates="payrolls")
    employee = relationship("Employee", back_populates="payrolls")

    __table_args__ = (
        Index("ix_payroll_tenant_employee_month", "tenant_id", "employee_id", "payroll_month", "payroll_year"),
        Index("ix_payroll_status", "status"),
    )


# =============================================================================
# Recruitment - Job Posting
# =============================================================================
class JobPosting(Base, AsyncAttrs):
    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    employment_type: Mapped[str] = mapped_column(String(50), default="full_time")
    experience_required: Mapped[Optional[str]] = mapped_column(String(100))
    salary_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    description: Mapped[Optional[str]] = mapped_column(Text)
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    criteria: Mapped[Optional[List[dict]]] = mapped_column(JSON)  # [{title, keywords, weight, required}]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    close_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))

    tenant = relationship("Tenant", back_populates="jobs")
    department = relationship("Department", back_populates=None)
    candidates = relationship("Candidate", back_populates="job_posting")
    interviews = relationship("AIInterview", back_populates="job_posting")

    __table_args__ = (
        Index("ix_jobs_tenant_active", "tenant_id", "is_active"),
    )


# =============================================================================
# Recruitment - Candidate
# =============================================================================
class Candidate(Base, AsyncAttrs):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    job_posting_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("job_postings.id", ondelete="SET NULL"), index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    current_position: Mapped[Optional[str]] = mapped_column(String(255))
    current_company: Mapped[Optional[str]] = mapped_column(String(255))
    years_experience: Mapped[Optional[int]] = mapped_column(Integer)
    education: Mapped[Optional[str]] = mapped_column(String(255))
    cv_url: Mapped[Optional[str]] = mapped_column(String(500))
    cv_text: Mapped[Optional[str]] = mapped_column(Text)
    cv_text_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)  # SHA256
    cv_raw_hash: Mapped[Optional[str]] = mapped_column(String(64))

    # AI Screening
    cv_score: Mapped[Optional[float]] = mapped_column(Float)
    cv_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    llm_extraction: Mapped[Optional[dict]] = mapped_column(JSON)

    # Stages
    stage: Mapped[str] = mapped_column(String(50), default="new", index=True)
    stage_history: Mapped[Optional[List[dict]]] = mapped_column(JSON)

    # Scoring
    interview_score: Mapped[Optional[float]] = mapped_column(Float)
    assessment_score: Mapped[Optional[float]] = mapped_column(Float)
    overall_score: Mapped[Optional[float]] = mapped_column(Float)

    # AI Interview
    ai_interview_url: Mapped[Optional[str]] = mapped_column(String(500))
    ai_interview_report: Mapped[Optional[dict]] = mapped_column(JSON)

    # Evaluation
    evaluated_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    evaluation_notes: Mapped[Optional[str]] = mapped_column(Text)
    hired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    source: Mapped[Optional[str]] = mapped_column(String(100))
    referred_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))

    tenant = relationship("Tenant", back_populates="candidates")
    job_posting = relationship("JobPosting", back_populates="candidates")
    interview = relationship("AIInterview", back_populates="candidate", uselist=False)

    __table_args__ = (
        Index("ix_candidates_tenant_stage", "tenant_id", "stage"),
        Index("ix_candidates_email", "tenant_id", "email"),
    )


# =============================================================================
# Recruitment - AI Interview
# =============================================================================
class AIInterview(Base, AsyncAttrs):
    __tablename__ = "ai_interviews"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True)
    job_posting_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("job_postings.id", ondelete="SET NULL"), index=True)
    invitation_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, started, completed, expired
    questions: Mapped[Optional[List[dict]]] = mapped_column(JSON)
    answers: Mapped[Optional[List[dict]]] = mapped_column(JSON)
    voice_transcript: Mapped[Optional[str]] = mapped_column(Text)
    evaluation: Mapped[Optional[dict]] = mapped_column(JSON)
    score: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    candidate = relationship("Candidate", back_populates="interview")
    job_posting = relationship("JobPosting", back_populates="interviews")

    __table_args__ = (
        Index("ix_interviews_tenant_status", "tenant_id", "status"),
    )


# =============================================================================
# Supply Chain - Inventory Product
# =============================================================================
class InventoryProduct(Base, AsyncAttrs):
    __tablename__ = "inventory_products"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    unit: Mapped[str] = mapped_column(String(50), default="piece")
    purchase_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    cost_method: Mapped[str] = mapped_column(String(50), default="weighted_average")
    current_stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    maximum_stock: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    warehouse_location: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))

    tenant = relationship("Tenant", back_populates="inventory_products")
    stock_movements = relationship("StockMovement", back_populates="product")
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="product")

    __table_args__ = (
        Index("ix_products_tenant_category", "tenant_id", "category"),
        Index("ix_products_stock", "current_stock"),
    )


# =============================================================================
# Supply Chain - Stock Movement
# =============================================================================
class StockMovement(Base, AsyncAttrs):
    __tablename__ = "stock_movements"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_products.id", ondelete="CASCADE"), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False)  # in, out, transfer, adjustment
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50))  # purchase_order, sales_order, manual
    reference_id: Mapped[Optional[str]] = mapped_column(String(255))
    from_location: Mapped[Optional[str]] = mapped_column(String(100))
    to_location: Mapped[Optional[str]] = mapped_column(String(100))
    cost_per_unit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    product = relationship("InventoryProduct", back_populates="stock_movements")

    __table_args__ = (
        Index("ix_movements_tenant_product", "tenant_id", "product_id"),
        Index("ix_movements_date", "created_at"),
    )


# =============================================================================
# Supply Chain - Supplier
# =============================================================================
class Supplier(Base, AsyncAttrs):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(Text)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50))
    payment_terms: Mapped[str] = mapped_column(String(100), default="Net 30")
    rating: Mapped[float] = mapped_column(Float, default=0)
    on_time_delivery_rate: Mapped[float] = mapped_column(Float, default=0)
    quality_rejection_rate: Mapped[float] = mapped_column(Float, default=0)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    tenant = relationship("Tenant", back_populates="suppliers")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

    __table_args__ = (
        Index("ix_suppliers_tenant", "tenant_id"),
    )


# =============================================================================
# Supply Chain - Purchase Order
# =============================================================================
class PurchaseOrder(Base, AsyncAttrs):
    __tablename__ = "purchase_orders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    po_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    supplier_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, approved, ordered, partially_received, received, cancelled
    request_date: Mapped[date] = mapped_column(Date, nullable=False)
    delivery_date: Mapped[Optional[date]] = mapped_column(Date)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    approved_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))

    tenant = relationship("Tenant", back_populates=None)
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="po", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_po_tenant_status", "tenant_id", "status"),
    )


# =============================================================================
# Supply Chain - Purchase Order Item
# =============================================================================
class PurchaseOrderItem(Base, AsyncAttrs):
    __tablename__ = "purchase_order_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_products.id", ondelete="SET NULL"), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    po = relationship("PurchaseOrder", back_populates="items")
    product = relationship("InventoryProduct", back_populates="purchase_order_items")


# =============================================================================
# Analytics - KPI Snapshot
# =============================================================================
class AnalyticsKPI(Base, AsyncAttrs):
    __tablename__ = "analytics_kpis"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    kpi_name: Mapped[str] = mapped_column(String(100), nullable=False)
    kpi_category: Mapped[str] = mapped_column(String(50))  # attendance, payroll, recruitment, supply_chain, employee
    value: Mapped[Optional[float]] = mapped_column(Float)
    value_text: Mapped[Optional[str]] = mapped_column(String(255))
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (
        Index("ix_kpi_tenant_category", "tenant_id", "kpi_category"),
        Index("ix_kpi_period", "period_start", "period_end"),
    )


# =============================================================================
# Analytics - Prediction
# =============================================================================
class Prediction(Base, AsyncAttrs):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # turnover, payroll, attendance, inventory
    entity_type: Mapped[str] = mapped_column(String(50))  # employee, department, company
    entity_id: Mapped[Optional[str]] = mapped_column(String(255))
    prediction_value: Mapped[Optional[float]] = mapped_column(Float)
    probability: Mapped[Optional[float]] = mapped_column(Float)
    factors: Mapped[Optional[List[dict]]] = mapped_column(JSON)
    timeframe: Mapped[Optional[str]] = mapped_column(String(50))  # "90 days", "next month"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_predictions_tenant_type", "tenant_id", "prediction_type"),
    )


# =============================================================================
# Audit Log
# =============================================================================
class AuditLog(Base, AsyncAttrs):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[Optional[str]] = mapped_column(String(255))
    old_values: Mapped[Optional[dict]] = mapped_column(JSON)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (
        Index("ix_audit_tenant", "tenant_id"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_created", "created_at"),
    )


# =============================================================================
# Performance Review
# =============================================================================
class PerformanceReview(Base, AsyncAttrs):
    __tablename__ = "performance_reviews"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    review_period: Mapped[str] = mapped_column(String(50))  # "2024-Q1", "2024-H1"
    reviewer_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"))
    overall_score: Mapped[Optional[float]] = mapped_column(Float)
    strengths: Mapped[Optional[str]] = mapped_column(Text)
    weaknesses: Mapped[Optional[str]] = mapped_column(Text)
    goals: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, submitted, reviewed, completed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))

    tenant = relationship("Tenant", back_populates=None)
    employee = relationship("Employee", back_populates="performance_reviews")
    reviewer = relationship("Employee", foreign_keys=[reviewer_id])

    __table_args__ = (
        Index("ix_reviews_tenant_employee", "tenant_id", "employee_id"),
        Index("ix_reviews_period", "review_period"),
    )
