"""
The H.R - Alembic Migration: Initial Schema
This migration creates the complete database schema for all HR modules.
Run with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # Enums (PostgreSQL ENUM types)
    # =========================================================================
    op.execute("""
        CREATE TYPE user_role_enum AS ENUM (
            'super_admin', 'company_admin', 'hr_manager', 'manager', 'employee', 'accountant'
        )
    """)
    op.execute("""
        CREATE TYPE employee_status_enum AS ENUM (
            'active', 'on_leave', 'terminated', 'probation', 'retired'
        )
    """)
    op.execute("""
        CREATE TYPE attendance_status_enum AS ENUM (
            'present', 'absent', 'late', 'half_day', 'on_leave', 'clocked_in', 'clocked_out'
        )
    """)
    op.execute("""
        CREATE TYPE leave_type_enum AS ENUM (
            'annual', 'sick', 'emergency', 'unpaid', 'maternity', 'paternity'
        )
    """)
    op.execute("""
        CREATE TYPE leave_status_enum AS ENUM ('pending', 'approved', 'rejected')
    """)
    op.execute("""
        CREATE TYPE payroll_status_enum AS ENUM ('draft', 'calculated', 'approved', 'paid')
    """)
    op.execute("""
        CREATE TYPE recruitment_stage_enum AS ENUM (
            'new', 'screening', 'interview', 'assessment', 'offer', 'hired', 'rejected'
        )
    """)
    op.execute("""
        CREATE TYPE gender_enum AS ENUM ('male', 'female')
    """)
    op.execute("""
        CREATE TYPE employment_type_enum AS ENUM ('full_time', 'part_time', 'contract', 'internship')
    """)

    # =========================================================================
    # Tenants (Companies)
    # =========================================================================
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('primary_color', sa.String(7), default='#0d6efd'),
        sa.Column('subscription_tier', sa.String(50), default='starter'),
        sa.Column('subscription_status', sa.String(50), default='active'),
        sa.Column('employee_count', sa.Integer, default=0),
        sa.Column('max_employees', sa.Integer, default=50),
        sa.Column('country', sa.String(100), default='EG'),
        sa.Column('currency', sa.String(3), default='EGP'),
        sa.Column('time_zone', sa.String(50), default='Africa/Cairo'),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # =========================================================================
    # Users (Authentication)
    # =========================================================================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('role', sa.String(50), nullable=False, default='employee'),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_attempts', sa.Integer, default=0),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_users_tenant_email', 'users', ['tenant_id', 'email'])

    # =========================================================================
    # Departments
    # =========================================================================
    op.create_table(
        'departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('manager_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sort_order', sa.Integer, default=0),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_departments_tenant', 'departments', ['tenant_id'])
    op.create_index('ix_departments_code', 'departments', ['tenant_id', 'code'])

    # =========================================================================
    # Employees
    # =========================================================================
    op.create_table(
        'employees',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('employee_number', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('national_id', sa.String(50), unique=True, nullable=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('father_name', sa.String(100), nullable=True),
        sa.Column('mother_name', sa.String(100), nullable=True),
        sa.Column('date_of_birth', sa.Date, nullable=True),
        sa.Column('gender', sa.String(20), nullable=True),
        sa.Column('marital_status', sa.String(20), nullable=True),
        sa.Column('nationality', sa.String(100), nullable=True),
        sa.Column('religion', sa.String(50), nullable=True),
        sa.Column('blood_type', sa.String(5), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('emergency_phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('social_insurance_number', sa.String(50), nullable=True),
        sa.Column('fingerprint_template', sa.Text, nullable=True),
        sa.Column('face_encoding', sa.Text, nullable=True),
        sa.Column('hire_date', sa.Date, nullable=True),
        sa.Column('probation_end', sa.Date, nullable=True),
        sa.Column('contract_start', sa.Date, nullable=True),
        sa.Column('contract_end', sa.Date, nullable=True),
        sa.Column('contract_type', sa.String(50), default='permanent'),
        sa.Column('status', sa.String(50), default='active', index=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('job_title', sa.String(255), nullable=True),
        sa.Column('employment_type', sa.String(50), default='full_time'),
        sa.Column('salary_base', sa.Numeric(12, 2), nullable=True),
        sa.Column('currency', sa.String(3), default='EGP'),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('terminated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('terminated_reason', sa.Text, nullable=True),
    )
    op.create_index('ix_employees_tenant_status', 'employees', ['tenant_id', 'status'])
    op.create_index('ix_employees_department', 'employees', ['department_id'])

    # =========================================================================
    # Attendance Records
    # =========================================================================
    op.create_table(
        'attendance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date', sa.Date, nullable=False, index=True),
        sa.Column('clock_in', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clock_out', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), default='present'),
        sa.Column('biometric_verified', sa.Boolean, default=False),
        sa.Column('biometric_device_id', sa.String(100), nullable=True),
        sa.Column('gps_lat', sa.Float, nullable=True),
        sa.Column('gps_lng', sa.Float, nullable=True),
        sa.Column('gps_accuracy', sa.Float, nullable=True),
        sa.Column('gps_verified', sa.Boolean, default=False),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('photo_verified', sa.Boolean, default=False),
        sa.Column('face_match_score', sa.Float, nullable=True),
        sa.Column('late_minutes', sa.Integer, default=0),
        sa.Column('early_departure_minutes', sa.Integer, default=0),
        sa.Column('total_hours', sa.Float, nullable=True),
        sa.Column('overtime_minutes', sa.Integer, default=0),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_attendance_tenant_employee_date', 'attendance_records', ['tenant_id', 'employee_id', 'date'])
    op.create_index('ix_attendance_date', 'attendance_records', ['date'])

    # =========================================================================
    # Leave Requests
    # =========================================================================
    op.create_table(
        'leave_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('leave_type', sa.String(50), nullable=False),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('total_days', sa.Integer, nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), default='pending', index=True),
        sa.Column('attachment_url', sa.String(500), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_leave_tenant_employee', 'leave_requests', ['tenant_id', 'employee_id'])
    op.create_index('ix_leave_status', 'leave_requests', ['status'])

    # =========================================================================
    # Employee Loans
    # =========================================================================
    op.create_table(
        'employee_loans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('loan_type', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('purpose', sa.String(255), nullable=True),
        sa.Column('request_date', sa.Date, nullable=False),
        sa.Column('repayment_start', sa.Date, nullable=False),
        sa.Column('repayment_end', sa.Date, nullable=True),
        sa.Column('monthly_installment', sa.Numeric(12, 2), default=0),
        sa.Column('remaining_balance', sa.Numeric(12, 2), default=0),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_loans_tenant_employee', 'employee_loans', ['tenant_id', 'employee_id'])

    # =========================================================================
    # Payroll
    # =========================================================================
    op.create_table(
        'payrolls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('payroll_month', sa.Integer, nullable=False),
        sa.Column('payroll_year', sa.Integer, nullable=False),
        sa.Column('period_start', sa.Date, nullable=False),
        sa.Column('period_end', sa.Date, nullable=False),
        sa.Column('base_salary', sa.Numeric(12, 2), default=0),
        sa.Column('housing_allowance', sa.Numeric(12, 2), default=0),
        sa.Column('transport_allowance', sa.Numeric(12, 2), default=0),
        sa.Column('meal_allowance', sa.Numeric(12, 2), default=0),
        sa.Column('phone_allowance', sa.Numeric(12, 2), default=0),
        sa.Column('other_allowances', sa.Numeric(12, 2), default=0),
        sa.Column('overtime_pay', sa.Numeric(12, 2), default=0),
        sa.Column('total_earnings', sa.Numeric(12, 2), default=0),
        sa.Column('absence_deduction', sa.Numeric(12, 2), default=0),
        sa.Column('late_deduction', sa.Numeric(12, 2), default=0),
        sa.Column('violation_deduction', sa.Numeric(12, 2), default=0),
        sa.Column('loan_repayment', sa.Numeric(12, 2), default=0),
        sa.Column('other_deductions', sa.Numeric(12, 2), default=0),
        sa.Column('total_deductions', sa.Numeric(12, 2), default=0),
        sa.Column('social_insurance_employee', sa.Numeric(12, 2), default=0),
        sa.Column('social_insurance_employer', sa.Numeric(12, 2), default=0),
        sa.Column('health_insurance', sa.Numeric(12, 2), default=0),
        sa.Column('taxable_income', sa.Numeric(12, 2), default=0),
        sa.Column('income_tax', sa.Numeric(12, 2), default=0),
        sa.Column('net_salary', sa.Numeric(12, 2), default=0),
        sa.Column('status', sa.String(50), default='draft', index=True),
        sa.Column('is_sent_to_employee', sa.Boolean, default=False),
        sa.Column('is_bank_transfer', sa.Boolean, default=True),
        sa.Column('bank_reference', sa.String(255), nullable=True),
        sa.Column('payslip_url', sa.String(500), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_payroll_tenant_employee_month', 'payrolls', ['tenant_id', 'employee_id', 'payroll_month', 'payroll_year'])
    op.create_index('ix_payroll_status', 'payrolls', ['status'])

    # =========================================================================
    # Recruitment - Job Postings
    # =========================================================================
    op.create_table(
        'job_postings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('employment_type', sa.String(50), default='full_time'),
        sa.Column('experience_required', sa.String(100), nullable=True),
        sa.Column('salary_min', sa.Numeric(12, 2), nullable=True),
        sa.Column('salary_max', sa.Numeric(12, 2), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('requirements', sa.Text, nullable=True),
        sa.Column('criteria', postgresql.JSONB, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('close_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_jobs_tenant_active', 'job_postings', ['tenant_id', 'is_active'])

    # =========================================================================
    # Recruitment - Candidates
    # =========================================================================
    op.create_table(
        'candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('job_posting_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_postings.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('current_position', sa.String(255), nullable=True),
        sa.Column('current_company', sa.String(255), nullable=True),
        sa.Column('years_experience', sa.Integer, nullable=True),
        sa.Column('education', sa.String(255), nullable=True),
        sa.Column('cv_url', sa.String(500), nullable=True),
        sa.Column('cv_text', sa.Text, nullable=True),
        sa.Column('cv_text_hash', sa.String(64), nullable=True, index=True),
        sa.Column('cv_raw_hash', sa.String(64), nullable=True),
        sa.Column('cv_score', sa.Float, nullable=True),
        sa.Column('cv_analysis', postgresql.JSONB, nullable=True),
        sa.Column('llm_extraction', postgresql.JSONB, nullable=True),
        sa.Column('stage', sa.String(50), default='new', index=True),
        sa.Column('stage_history', postgresql.JSONB, nullable=True),
        sa.Column('interview_score', sa.Float, nullable=True),
        sa.Column('assessment_score', sa.Float, nullable=True),
        sa.Column('overall_score', sa.Float, nullable=True),
        sa.Column('ai_interview_url', sa.String(500), nullable=True),
        sa.Column('ai_interview_report', postgresql.JSONB, nullable=True),
        sa.Column('evaluated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('evaluation_notes', sa.Text, nullable=True),
        sa.Column('hired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('referred_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_candidates_tenant_stage', 'candidates', ['tenant_id', 'stage'])
    op.create_index('ix_candidates_email', 'candidates', ['tenant_id', 'email'])

    # =========================================================================
    # Recruitment - AI Interviews
    # =========================================================================
    op.create_table(
        'ai_interviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('job_posting_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_postings.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('invitation_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('questions', postgresql.JSONB, nullable=True),
        sa.Column('answers', postgresql.JSONB, nullable=True),
        sa.Column('voice_transcript', sa.Text, nullable=True),
        sa.Column('evaluation', postgresql.JSONB, nullable=True),
        sa.Column('score', sa.Float, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_interviews_tenant_status', 'ai_interviews', ['tenant_id', 'status'])

    # =========================================================================
    # Supply Chain - Inventory Products
    # =========================================================================
    op.create_table(
        'inventory_products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('sku', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('barcode', sa.String(100), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(100), nullable=True, index=True),
        sa.Column('unit', sa.String(50), default='piece'),
        sa.Column('purchase_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('selling_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('cost_method', sa.String(50), default='weighted_average'),
        sa.Column('current_stock', sa.Numeric(12, 2), default=0),
        sa.Column('minimum_stock', sa.Numeric(12, 2), default=0),
        sa.Column('maximum_stock', sa.Numeric(12, 2), nullable=True),
        sa.Column('warehouse_location', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_products_tenant_category', 'inventory_products', ['tenant_id', 'category'])
    op.create_index('ix_products_stock', 'inventory_products', ['current_stock'])

    # =========================================================================
    # Supply Chain - Stock Movements
    # =========================================================================
    op.create_table(
        'stock_movements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('inventory_products.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('movement_type', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', sa.String(255), nullable=True),
        sa.Column('from_location', sa.String(100), nullable=True),
        sa.Column('to_location', sa.String(100), nullable=True),
        sa.Column('cost_per_unit', sa.Numeric(12, 2), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_movements_tenant_product', 'stock_movements', ['tenant_id', 'product_id'])
    op.create_index('ix_movements_date', 'stock_movements', ['created_at'])

    # =========================================================================
    # Supply Chain - Suppliers
    # =========================================================================
    op.create_table(
        'suppliers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('contact_person', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('tax_id', sa.String(50), nullable=True),
        sa.Column('payment_terms', sa.String(100), default='Net 30'),
        sa.Column('rating', sa.Float, default=0),
        sa.Column('on_time_delivery_rate', sa.Float, default=0),
        sa.Column('quality_rejection_rate', sa.Float, default=0),
        sa.Column('is_blacklisted', sa.Boolean, default=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_suppliers_tenant', 'suppliers', ['tenant_id'])

    # =========================================================================
    # Supply Chain - Purchase Orders
    # =========================================================================
    op.create_table(
        'purchase_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('po_number', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('request_date', sa.Date, nullable=False),
        sa.Column('delivery_date', sa.Date, nullable=True),
        sa.Column('total_amount', sa.Numeric(12, 2), default=0),
        sa.Column('tax_amount', sa.Numeric(12, 2), default=0),
        sa.Column('grand_total', sa.Numeric(12, 2), default=0),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_po_tenant_status', 'purchase_orders', ['tenant_id', 'status'])

    # =========================================================================
    # Supply Chain - Purchase Order Items
    # =========================================================================
    op.create_table(
        'purchase_order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('inventory_products.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('total_price', sa.Numeric(12, 2), default=0),
        sa.Column('received_quantity', sa.Numeric(12, 2), default=0),
    )

    # =========================================================================
    # Analytics - KPI Snapshots
    # =========================================================================
    op.create_table(
        'analytics_kpis',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('kpi_name', sa.String(100), nullable=False),
        sa.Column('kpi_category', sa.String(50)),
        sa.Column('value', sa.Float, nullable=True),
        sa.Column('value_text', sa.String(255), nullable=True),
        sa.Column('period_start', sa.Date, nullable=False),
        sa.Column('period_end', sa.Date, nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_kpi_tenant_category', 'analytics_kpis', ['tenant_id', 'kpi_category'])
    op.create_index('ix_kpi_period', 'analytics_kpis', ['period_start', 'period_end'])

    # =========================================================================
    # Analytics - Predictions
    # =========================================================================
    op.create_table(
        'predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('prediction_type', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50)),
        sa.Column('entity_id', sa.String(255), nullable=True),
        sa.Column('prediction_value', sa.Float, nullable=True),
        sa.Column('probability', sa.Float, nullable=True),
        sa.Column('factors', postgresql.JSONB, nullable=True),
        sa.Column('timeframe', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('alert_sent', sa.Boolean, default=False),
    )
    op.create_index('ix_predictions_tenant_type', 'predictions', ['tenant_id', 'prediction_type'])

    # =========================================================================
    # Audit Log
    # =========================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50)),
        sa.Column('entity_id', sa.String(255), nullable=True),
        sa.Column('old_values', postgresql.JSONB, nullable=True),
        sa.Column('new_values', postgresql.JSONB, nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_audit_tenant', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_created', 'audit_logs', ['created_at'])

    # =========================================================================
    # Performance Reviews
    # =========================================================================
    op.create_table(
        'performance_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('review_period', sa.String(50)),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('overall_score', sa.Float, nullable=True),
        sa.Column('strengths', sa.Text, nullable=True),
        sa.Column('weaknesses', sa.Text, nullable=True),
        sa.Column('goals', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_reviews_tenant_employee', 'performance_reviews', ['tenant_id', 'employee_id'])
    op.create_index('ix_reviews_period', 'performance_reviews', ['review_period'])
