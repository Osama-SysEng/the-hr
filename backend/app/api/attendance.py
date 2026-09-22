"""
The H.R - Attendance API Router
Clock-in/out, attendance records, reports
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import (
    AttendanceRecord, Employee, Tenant, Department
)
import uuid


router = APIRouter(prefix="/attendance", tags=["Attendance"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


class ClockInRequest(BaseModel):
    biometric_data: Optional[str] = None  # Base64 encoded fingerprint or face
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    gps_accuracy: Optional[float] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    biometric_data: Optional[str] = None
    notes: Optional[str] = None


class AttendanceRecordResponse(BaseModel):
    id: str
    employee_id: str
    employee_number: str
    employee_name: str
    date: date
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    status: str
    biometric_verified: bool
    gps_verified: bool
    photo_verified: bool
    face_match_score: Optional[float] = None
    late_minutes: int
    early_departure_minutes: int
    total_hours: Optional[float] = None
    overtime_minutes: int
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceListResponse(BaseModel):
    records: List[AttendanceRecordResponse]
    total: int
    page: int
    page_size: int


class DailyAttendanceResponse(BaseModel):
    date: date
    total_employees: int
    present: int
    absent: int
    late: int
    on_leave: int
    holiday: int
    attendance_rate: float


class AttendanceReportRequest(BaseModel):
    start_date: date
    end_date: date
    department_id: Optional[str] = None
    status: Optional[str] = None


class AttendanceReportResponse(BaseModel):
    start_date: date
    end_date: date
    total_records: int
    present_count: int
    absent_count: int
    late_count: int
    on_leave_count: int
    average_hours: float
    average_overtime_minutes: float
    by_department: List[dict]
    by_day: List[dict]


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------
def _build_attendance_response(record: AttendanceRecord, employee: Employee) -> AttendanceRecordResponse:
    return AttendanceRecordResponse(
        id=record.id,
        employee_id=record.employee_id,
        employee_number=employee.employee_number,
        employee_name=f"{employee.first_name} {employee.last_name}",
        date=record.date,
        clock_in=record.clock_in,
        clock_out=record.clock_out,
        status=record.status,
        biometric_verified=record.biometric_verified,
        gps_verified=record.gps_verified,
        photo_verified=record.photo_verified,
        face_match_score=record.face_match_score,
        late_minutes=record.late_minutes,
        early_departure_minutes=record.early_departure_minutes,
        total_hours=record.total_hours,
        overtime_minutes=record.overtime_minutes,
        notes=record.notes,
        created_at=record.created_at,
    )


# -----------------------------------------------------------------------------
# Clock In
# -----------------------------------------------------------------------------
@router.post("/clock-in", status_code=status.HTTP_201_CREATED)
async def clock_in(
    request: ClockInRequest,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل دخول الموظف (_clock-in)_"""
    current_user = await get_current_user(credentials, db)
    employee_id = current_user.get("employee_id")

    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ليس لديك صلاحية تسجيل الدخول كموظف",
        )

    tenant_id = current_user["tenant_id"]
    today = date.today()

    # Check if already clocked in today
    result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date == today,
                AttendanceRecord.tenant_id == tenant_id,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.clock_in and not existing.clock_out:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لقد قمت بتسجيل الدخول بالفعل اليوم",
            )
        # Re-clock-in after clocking out
        existing.clock_in = datetime.now(timezone.utc)
        existing.clock_out = None
        existing.status = "clocked_in"
        existing.biometric_verified = bool(request.biometric_data)
        existing.gps_lat = request.gps_lat
        existing.gps_lng = request.gps_lng
        existing.gps_accuracy = request.gps_accuracy
        existing.gps_verified = bool(request.gps_lat and request.gps_lng)
        existing.photo_url = request.photo_url
        existing.notes = request.notes
        await db.commit()
        await db.refresh(existing)
        return {"message": "تم تسجيل الدخول بنجاح", "record": _build_attendance_response(existing, existing.employee)}

    # Create new attendance record
    record = AttendanceRecord(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        employee_id=employee_id,
        date=today,
        clock_in=datetime.now(timezone.utc),
        status="clocked_in",
        biometric_verified=bool(request.biometric_data),
        gps_lat=request.gps_lat,
        gps_lng=request.gps_lng,
        gps_accuracy=request.gps_accuracy,
        gps_verified=bool(request.gps_lat and request.gps_lng),
        photo_url=request.photo_url,
        notes=request.notes,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "message": "تم تسجيل الدخول بنجاح",
        "record": _build_attendance_response(record, record.employee),
    }


# -----------------------------------------------------------------------------
# Clock Out
# -----------------------------------------------------------------------------
@router.post("/clock-out")
async def clock_out(
    request: ClockOutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل خروج الموظف (clock-out)"""
    current_user = await get_current_user(credentials, db)
    employee_id = current_user.get("employee_id")

    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ليس لديك صلاحية تسجيل الخروج",
        )

    tenant_id = current_user["tenant_id"]
    today = date.today()

    result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date == today,
                AttendanceRecord.tenant_id == tenant_id,
            )
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="لا توجد سجلات حضور لهذا اليوم",
        )

    if not record.clock_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لم تقم بتسجيل الدخول اليوم",
        )

    if record.clock_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لقد قمت بتسجيل الخروج بالفعل",
        )

    # Calculate hours
    clock_in_time = record.clock_in
    clock_out_time = datetime.now(timezone.utc)
    total_seconds = (clock_out_time - clock_in_time).total_seconds()
    total_hours = total_seconds / 3600

    record.clock_out = clock_out_time
    record.status = "present"
    record.total_hours = round(total_hours, 2)
    record.biometric_verified = bool(request.biometric_data) or record.biometric_verified
    record.notes = request.notes

    # Calculate late minutes (if clock-in after 9:00 AM)
    if clock_in_time.hour >= 9 and clock_in_time.minute > 0:
        late_minutes = (clock_in_time.hour - 9) * 60 + clock_in_time.minute
        record.late_minutes = late_minutes

    # Calculate overtime (if > 8 hours)
    if total_hours > 8:
        overtime_minutes = int((total_hours - 8) * 60)
        record.overtime_minutes = overtime_minutes

    await db.commit()
    await db.refresh(record)

    return {
        "message": "تم تسجيل الخروج بنجاح",
        "record": _build_attendance_response(record, record.employee),
        "total_hours": record.total_hours,
        "overtime_minutes": record.overtime_minutes,
    }


# -----------------------------------------------------------------------------
# Get Today's Attendance
# -----------------------------------------------------------------------------
@router.get("/today")
async def get_today_attendance(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على حضور اليوم للموظف الحالي"""
    current_user = await get_current_user(credentials, db)
    employee_id = current_user.get("employee_id")
    tenant_id = current_user["tenant_id"]
    today = date.today()

    if employee_id:
        result = await db.execute(
            select(AttendanceRecord).where(
                and_(
                    AttendanceRecord.employee_id == employee_id,
                    AttendanceRecord.date == today,
                    AttendanceRecord.tenant_id == tenant_id,
                )
            )
            .options(select.attendance_record.employee)
        )
        record = result.scalar_one_or_none()

        if record:
            return {
                "date": record.date,
                "clock_in": record.clock_in,
                "clock_out": record.clock_out,
                "status": record.status,
                "total_hours": record.total_hours,
                "overtime_minutes": record.overtime_minutes,
                "late_minutes": record.late_minutes,
            }

    return {
        "date": today,
        "clock_in": None,
        "clock_out": None,
        "status": "absent",
        "message": "لم تقم بتسجيل الدخول اليوم",
    }


# -----------------------------------------------------------------------------
# List Attendance Records (Admin)
# -----------------------------------------------------------------------------
@router.get("/records", response_model=AttendanceListResponse)
async def list_attendance_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    employee_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    department_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """قائمة سجلات الحضور (للمدراء)"""
    tenant_id = current_user["tenant_id"]

    query = select(AttendanceRecord).where(AttendanceRecord.tenant_id == tenant_id)

    if start_date:
        query = query.where(AttendanceRecord.date >= start_date)
    if end_date:
        query = query.where(AttendanceRecord.date <= end_date)
    if employee_id:
        query = query.where(AttendanceRecord.employee_id == employee_id)
    if status:
        query = query.where(AttendanceRecord.status == status)
    if department_id:
        query = query.join(Employee).where(Employee.department_id == department_id)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sort and paginate
    query = query.order_by(AttendanceRecord.date.desc(), AttendanceRecord.clock_in.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    records = result.scalars().all()

    # Load employee for each record
    response_records = []
    for record in records:
        emp_result = await db.execute(
            select(Employee).where(Employee.id == record.employee_id)
        )
        employee = emp_result.scalar_one_or_none()
        response_records.append(_build_attendance_response(record, employee or Employee(
            first_name="Unknown", last_name="Unknown", employee_number="???",
            id=record.employee_id, tenant_id=tenant_id
        )))

    return AttendanceListResponse(
        records=response_records,
        total=total,
        page=page,
        page_size=page_size,
    )


# -----------------------------------------------------------------------------
# Daily Attendance Report
# -----------------------------------------------------------------------------
@router.get("/report/daily", response_model=DailyAttendanceResponse)
async def daily_attendance_report(
    report_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """تقرير الحضور اليومي"""
    tenant_id = current_user["tenant_id"]
    report_date = report_date or date.today()

    # Count total employees
    total_result = await db.execute(
        select(func.count(Employee.id)).where(
            and_(Employee.tenant_id == tenant_id, Employee.status == "active")
        )
    )
    total_employees = total_result.scalar() or 0

    if total_employees == 0:
        return DailyAttendanceResponse(
            date=report_date,
            total_employees=0, present=0, absent=0, late=0, on_leave=0, holiday=0,
            attendance_rate=0.0,
        )

    # Count attendance
    attendance_result = await db.execute(
        select(
            func.count(AttendanceRecord.id).label("total"),
            func.sum(func.cast(AttendanceRecord.status == "present", Integer)).label("present"),
            func.sum(func.cast(AttendanceRecord.status == "absent", Integer)).label("absent"),
            func.sum(func.cast(AttendanceRecord.status == "late", Integer)).label("late"),
        ).where(
            and_(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.date == report_date,
            )
        )
    )
    attendance = attendance_result.one()

    present = attendance.present or 0
    absent = attendance.absent or 0
    late = attendance.late or 0

    return DailyAttendanceResponse(
        date=report_date,
        total_employees=total_employees,
        present=present,
        absent=absent,
        late=late,
        on_leave=0,
        holiday=0,
        attendance_rate=round((present / total_employees) * 100, 2) if total_employees > 0 else 0.0,
    )


# -----------------------------------------------------------------------------
# Period Attendance Report
# -----------------------------------------------------------------------------
@router.post("/report/period", response_model=AttendanceReportResponse)
async def period_attendance_report(
    request: AttendanceReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """تقرير الحضور لفترة زمنية"""
    tenant_id = current_user["tenant_id"]

    query = select(AttendanceRecord).where(
        and_(
            AttendanceRecord.tenant_id == tenant_id,
            AttendanceRecord.date >= request.start_date,
            AttendanceRecord.date <= request.end_date,
        )
    )

    if request.department_id:
        query = query.join(Employee).where(Employee.department_id == request.department_id)
    if request.status:
        query = query.where(AttendanceRecord.status == request.status)

    result = await db.execute(query)
    records = result.scalars().all()

    present_count = sum(1 for r in records if r.status == "present")
    absent_count = sum(1 for r in records if r.status == "absent")
    late_count = sum(1 for r in records if r.status == "late")
    on_leave_count = sum(1 for r in records if r.status == "on_leave")
    total_hours = sum((r.total_hours or 0) for r in records)
    total_overtime = sum(r.overtime_minutes for r in records)

    # By department
    dept_query = select(Employee.department_id, func.count(AttendanceRecord.id)).join(
        AttendanceRecord, AttendanceRecord.employee_id == Employee.id
    ).where(
        and_(
            Employee.tenant_id == tenant_id,
            AttendanceRecord.tenant_id == tenant_id,
            AttendanceRecord.date >= request.start_date,
            AttendanceRecord.date <= request.end_date,
        )
    ).group_by(Employee.department_id)

    dept_result = await db.execute(dept_query)
    by_department = []
    for row in dept_result:
        dept_id = row.department_id
        dept_name_result = await db.execute(
            select(Department.name).where(Department.id == dept_id)
        )
        dept_name = dept_name_result.scalar() or "غير محدد"
        by_department.append({
            "department_id": dept_id,
            "department_name": dept_name,
            "total_records": row.total,
        })

    # By day
    by_day_query = select(
        AttendanceRecord.date,
        func.count(AttendanceRecord.id).label("total"),
        func.sum(func.cast(AttendanceRecord.status == "present", Integer)).label("present"),
    ).where(
        and_(
            AttendanceRecord.tenant_id == tenant_id,
            AttendanceRecord.date >= request.start_date,
            AttendanceRecord.date <= request.end_date,
        )
    ).group_by(AttendanceRecord.date).order_by(AttendanceRecord.date)

    by_day_result = await db.execute(by_day_query)
    by_day = []
    for row in by_day_result:
        by_day.append({
            "date": row.date,
            "total": row.total,
            "present": row.present or 0,
            "absent": row.total - (row.present or 0),
        })

    return AttendanceReportResponse(
        start_date=request.start_date,
        end_date=request.end_date,
        total_records=len(records),
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        on_leave_count=on_leave_count,
        average_hours=round(total_hours / len(records), 2) if records else 0.0,
        average_overtime_minutes=round(total_overtime / len(records), 2) if records else 0.0,
        by_department=by_department,
        by_day=by_day,
    )
