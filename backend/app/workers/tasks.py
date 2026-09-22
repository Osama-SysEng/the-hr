"""
The H.R - Celery Background Tasks
"""

from celery import shared_task
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.core.database import async_session_factory
from app.models.models import Payroll, AttendanceRecord, Employee, LeaveRequest, Candidate
from app.services.email_service import EmailService
from app.services.sms_service import SMSService


@shared_task(bind=True, max_retries=3)
def send_payslip_email_task(self, employee_id: str, payroll_id: str):
    try:
        email_service = EmailService()
        async with async_session_factory() as db:
            payroll = await db.get(Payroll, payroll_id)
            employee = await db.get(Employee, employee_id)
            if not payroll or not employee:
                return {"error": "Not found"}
            email_service.send_payslip_email(
                employee_email=employee.email,
                employee_name=f"{employee.first_name} {employee.last_name}",
                payroll_month=payroll.payroll_month,
                payroll_year=payroll.payroll_year,
                net_salary=float(payroll.net_salary),
                payslip_path=payroll.payslip_url,
            )
            return {"success": True}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_interview_invitation_task(self, candidate_id: str):
    try:
        email_service = EmailService()
        sms_service = SMSService()
        async with async_session_factory() as db:
            candidate = await db.get(Candidate, candidate_id)
            if not candidate:
                return {"error": "Not found"}
            interview_url = f"https://the-hr.puter.app/interview/{candidate_id}"
            email_service.send_interview_invitation(
                candidate_email=candidate.email,
                candidate_name=f"{candidate.first_name} {candidate.last_name}",
                interview_url=interview_url,
                job_title=candidate.current_position or "الإدارة المطلوبة",
            )
            if candidate.phone:
                sms_service.send_sms(candidate.phone, f"دعوة مقابلة: {interview_url}")
            return {"success": True}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_attendance_notification_task(self, attendance_id: str):
    try:
        email_service = EmailService()
        async with async_session_factory() as db:
            attendance = await db.get(AttendanceRecord, attendance_id)
            if not attendance:
                return {"error": "Not found"}
            employee = await db.get(Employee, attendance.employee_id)
            if employee and employee.department and employee.department.manager_id:
                manager = await db.get(Employee, employee.department.manager_id)
                if manager and manager.email:
                    email_service.send_attendance_notification(
                        manager_email=manager.email,
                        manager_name=f"{manager.first_name} {manager.last_name}",
                        employee_name=f"{employee.first_name} {employee.last_name}",
                        employee_number=employee.employee_number,
                        attendance_status=attendance.status,
                        date=str(attendance.date),
                        details=f"Total: {attendance.total_hours}h, Late: {attendance.late_minutes}m",
                    )
            return {"success": True}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def calculate_payroll_task(self, employee_id: str, month: int, year: int):
    try:
        async with async_session_factory() as db:
            employee = await db.get(Employee, employee_id)
            if not employee:
                return {"error": "Not found"}
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year, 12, 31)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
            base = employee.salary_base or Decimal("5000")
            payroll = Payroll(
                id=str(uuid.uuid4()),
                tenant_id=employee.tenant_id,
                employee_id=employee_id,
                payroll_month=month,
                payroll_year=year,
                period_start=start_date,
                period_end=end_date,
                base_salary=base,
                housing_allowance=base * Decimal("0.25"),
                transport_allowance=base * Decimal("0.10"),
                meal_allowance=base * Decimal("0.05"),
                total_earnings=base * Decimal("1.40"),
                total_deductions=Decimal("0"),
                social_insurance_employee=base * Decimal("0.11"),
                social_insurance_employer=base * Decimal("0.1875"),
                health_insurance=base * Decimal("0.01"),
                net_salary=base * Decimal("1.40") - base * Decimal("0.12") - base * Decimal("0.01"),
                status="calculated",
                calculated_at=datetime.now(),
            )
            db.add(payroll)
            await db.commit()
            return {"success": True, "payroll_id": payroll.id}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def cleanup_old_data_task(self, days: int = 90):
    try:
        async with async_session_factory() as db:
            cutoff = date.today() - timedelta(days=days)
            result = await db.execute(
                AttendanceRecord.__table__.delete().where(AttendanceRecord.date < cutoff)
            )
            await db.commit()
            return {"success": True, "deleted": result.rowcount}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)
