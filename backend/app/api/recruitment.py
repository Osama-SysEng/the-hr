"""
The H.R - Recruitment API Router
AI CV Screening, Job Postings, Candidates, AI Interviews
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import (
    Candidate, JobPosting, AIInterview, Tenant, Employee, Department
)
import uuid
import shutil
import os


router = APIRouter(prefix="/recruitment", tags=["Recruitment"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from decimal import Decimal as PyDecimal


class JobCriteria(BaseModel):
    title: str
    keywords: str
    weight: int = Field(ge=1, le=100)
    required: bool = False


class JobPostingCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    department_id: Optional[str] = None
    location: Optional[str] = None
    employment_type: str = "full_time"
    experience_required: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    criteria: List[JobCriteria] = []
    close_at: Optional[datetime] = None


class JobPostingUpdateRequest(BaseModel):
    title: Optional[str] = None
    department_id: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_required: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    criteria: Optional[List[JobCriteria]] = None
    close_at: Optional[datetime] = None


class JobPostingResponse(BaseModel):
    id: str
    title: str
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    location: Optional[str] = None
    employment_type: str
    experience_required: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    criteria: List[dict] = []
    is_active: bool
    posted_at: Optional[datetime] = None
    close_at: Optional[datetime] = None
    candidate_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CandidateCreateRequest(BaseModel):
    job_posting_id: Optional[str] = None
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str
    phone: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    current_position: Optional[str] = None
    current_company: Optional[str] = None
    years_experience: Optional[int] = None
    education: Optional[str] = None
    source: Optional[str] = None
    referred_by: Optional[str] = None
    notes: Optional[str] = None


class CandidateResponse(BaseModel):
    id: str
    job_posting_id: Optional[str] = None
    job_title: Optional[str] = None
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    current_position: Optional[str] = None
    current_company: Optional[str] = None
    years_experience: Optional[int] = None
    education: Optional[str] = None
    cv_url: Optional[str] = None
    cv_score: Optional[float] = None
    stage: str
    cv_analysis: Optional[dict] = None
    llm_extraction: Optional[dict] = None
    evaluated_by: Optional[str] = None
    evaluation_notes: Optional[str] = None
    hired_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CandidateListResponse(BaseModel):
    candidates: List[CandidateResponse]
    total: int
    page: int
    page_size: int


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------
def _build_job_response(job: JobPosting, dept: Optional[Department], candidate_count: int) -> JobPostingResponse:
    return JobPostingResponse(
        id=job.id,
        title=job.title,
        department_id=job.department_id,
        department_name=dept.name if dept else None,
        location=job.location,
        employment_type=job.employment_type,
        experience_required=job.experience_required,
        salary_min=float(job.salary_min) if job.salary_min else None,
        salary_max=float(job.salary_max) if job.salary_max else None,
        description=job.description,
        requirements=job.requirements,
        criteria=job.criteria or [],
        is_active=job.is_active,
        posted_at=job.posted_at,
        close_at=job.close_at,
        candidate_count=candidate_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _build_candidate_response(candidate: Candidate, job: Optional[JobPosting]) -> CandidateResponse:
    return CandidateResponse(
        id=candidate.id,
        job_posting_id=candidate.job_posting_id,
        job_title=job.title if job else None,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        full_name=f"{candidate.first_name} {candidate.last_name}",
        email=candidate.email,
        phone=candidate.phone,
        country=candidate.country,
        city=candidate.city,
        current_position=candidate.current_position,
        current_company=candidate.current_company,
        years_experience=candidate.years_experience,
        education=candidate.education,
        cv_url=candidate.cv_url,
        cv_score=candidate.cv_score,
        stage=candidate.stage,
        cv_analysis=candidate.cv_analysis,
        llm_extraction=candidate.llm_extraction,
        evaluated_by=candidate.evaluated_by,
        evaluation_notes=candidate.evaluation_notes,
        hired_at=candidate.hired_at,
        rejection_reason=candidate.rejection_reason,
        source=candidate.source,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


# -----------------------------------------------------------------------------
# Job Postings
# -----------------------------------------------------------------------------
@router.get("/jobs", response_model=List[JobPostingResponse])
async def list_jobs(
    active_only: bool = Query(True),
    department_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """قائمة وظائف العمل"""
    tenant_id = current_user["tenant_id"]

    query = select(JobPosting).where(JobPosting.tenant_id == tenant_id)
    if active_only:
        query = query.where(JobPosting.is_active == True)
    if department_id:
        query = query.where(JobPosting.department_id == department_id)

    query = query.order_by(JobPosting.created_at.desc())
    result = await db.execute(query)
    jobs = result.scalars().all()

    response = []
    for job in jobs:
        dept_result = await db.execute(
            select(Department).where(Department.id == job.department_id)
        )
        dept = dept_result.scalar_one_or_none()

        # Count candidates
        cand_result = await db.execute(
            select(func.count(Candidate.id)).where(
                and_(Candidate.job_posting_id == job.id, Candidate.tenant_id == tenant_id)
            )
        )
        cand_count = cand_result.scalar() or 0

        response.append(_build_job_response(job, dept, cand_count))

    return response


@router.get("/jobs/{job_id}", response_model=JobPostingResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """الحصول على وظيفة محددة"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(JobPosting)
        .where(and_(JobPosting.id == job_id, JobPosting.tenant_id == tenant_id))
        .options(selectinload(JobPosting.department))
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الوظيفة غير موجودة",
        )

    dept = job.department
    cand_result = await db.execute(
        select(func.count(Candidate.id)).where(
            and_(Candidate.job_posting_id == job.id, Candidate.tenant_id == tenant_id)
        )
    )
    cand_count = cand_result.scalar() or 0

    return _build_job_response(job, dept, cand_count)


@router.post("/jobs", response_model=JobPostingResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: JobPostingCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """إنشاء وظيفة جديدة"""
    tenant_id = current_user["tenant_id"]

    job = JobPosting(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        **request.model_dump(),
        is_active=True,
        posted_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Load department
    if job.department_id:
        dept_result = await db.execute(
            select(Department).where(Department.id == job.department_id)
        )
        dept = dept_result.scalar_one_or_none()
    else:
        dept = None

    return _build_job_response(job, dept, 0)


@router.put("/jobs/{job_id}", response_model=JobPostingResponse)
async def update_job(
    job_id: str,
    request: JobPostingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """تحديث وظيفة"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(JobPosting)
        .where(and_(JobPosting.id == job_id, JobPosting.tenant_id == tenant_id))
        .options(selectinload(JobPosting.department))
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الوظيفة غير موجودة",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)

    dept = job.department
    cand_result = await db.execute(
        select(func.count(Candidate.id)).where(
            and_(Candidate.job_posting_id == job.id, Candidate.tenant_id == tenant_id)
        )
    )
    cand_count = cand_result.scalar() or 0

    return _build_job_response(job, dept, cand_count)


@router.post("/jobs/{job_id}/close")
async def close_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """إغلاق وظيفة (إيقاف تلقين المرشحين الجدد)"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(JobPosting).where(
            and_(JobPosting.id == job_id, JobPosting.tenant_id == tenant_id)
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الوظيفة غير موجودة",
        )

    job.is_active = False
    await db.commit()

    return {"message": "تم إغلاق الوظيفة", "is_active": job.is_active}


# -----------------------------------------------------------------------------
# Candidates
# -----------------------------------------------------------------------------
@router.get("/candidates", response_model=CandidateListResponse)
async def list_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    job_posting_id: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """قائمة المرشحين"""
    tenant_id = current_user["tenant_id"]

    query = select(Candidate).where(Candidate.tenant_id == tenant_id)

    if job_posting_id:
        query = query.where(Candidate.job_posting_id == job_posting_id)
    if stage:
        query = query.where(Candidate.stage == stage)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Candidate.first_name.ilike(search_term),
                Candidate.last_name.ilike(search_term),
                Candidate.email.ilike(search_term),
            )
        )

    query = query.order_by(Candidate.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(query)
    candidates = result.scalars().all()

    response = []
    for candidate in candidates:
        job_result = await db.execute(
            select(JobPosting).where(JobPosting.id == candidate.job_posting_id)
        )
        job = job_result.scalar_one_or_none()
        response.append(_build_candidate_response(candidate, job))

    return CandidateListResponse(
        candidates=response,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/candidates", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    request: CandidateCreateRequest,
    cv_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """إضافة مرشح جديد"""
    tenant_id = current_user["tenant_id"]

    # Save CV file
    cv_url = None
    cv_text = None
    if cv_file:
        upload_dir = os.path.join("uploads", tenant_id)
        os.makedirs(upload_dir, exist_ok=True)
        cv_filename = f"{uuid.uuid4().hex}_{cv_file.filename}"
        cv_path = os.path.join(upload_dir, cv_filename)
        with open(cv_path, "wb") as buffer:
            shutil.copyfileobj(cv_file.file, buffer)
        cv_url = f"/uploads/{tenant_id}/{cv_filename}"

        # Extract CV text
        try:
            import pdfplumber
            with pdfplumber.open(cv_path) as pdf:
                cv_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        except Exception:
            try:
                import mammoth
                with open(cv_path, "rb") as f:
                    result = mammoth.extract_raw_text(f)
                    cv_text = result.value
            except Exception:
                cv_text = ""

    candidate = Candidate(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        job_posting_id=request.job_posting_id,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        phone=request.phone,
        country=request.country,
        city=request.city,
        current_position=request.current_position,
        current_company=request.current_company,
        years_experience=request.years_experience,
        education=request.education,
        cv_url=cv_url,
        cv_text=cv_text,
        source=request.source,
        notes=request.notes,
        stage="new",
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)

    job_result = await db.execute(
        select(JobPosting).where(JobPosting.id == candidate.job_posting_id)
    )
    job = job_result.scalar_one_or_none()

    return _build_candidate_response(candidate, job)


@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """الحصول على مرشح محدد"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Candidate)
        .where(and_(Candidate.id == candidate_id, Candidate.tenant_id == tenant_id))
        .options(selectinload(Candidate.job_posting))
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المرشح غير موجود",
        )

    return _build_candidate_response(candidate, candidate.job_posting)


@router.put("/candidates/{candidate_id}/stage")
async def update_candidate_stage(
    candidate_id: str,
    new_stage: str = Query(...),
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """تحديث مرحلة المرشح"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Candidate).where(
            and_(Candidate.id == candidate_id, Candidate.tenant_id == tenant_id)
        )
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المرشح غير موجود",
        )

    # Track stage history
    history = candidate.stage_history or []
    history.append({
        "from": candidate.stage,
        "to": new_stage,
        "changed_by": current_user["user_id"],
        "changed_at": datetime.now(timezone.utc).isoformat(),
    })
    candidate.stage_history = history
    candidate.stage = new_stage
    if notes:
        candidate.evaluation_notes = notes

    # If hired, record date
    if new_stage == "hired":
        candidate.hired_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "message": "تم تحديث المرحلة",
        "candidate": _build_candidate_response(candidate, candidate.job_posting),
    }


# -----------------------------------------------------------------------------
# AI CV Screening
# -----------------------------------------------------------------------------
@router.post("/candidates/{candidate_id}/screen")
async def screen_candidate(
    candidate_id: str,
    job_criteria: Optional[List[dict]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager", "hr_manager")),
):
    """
    فحص سير المرشح ذاتياً باستخدام AI
    يعتمد على MY-CV screen algorithm + LLM extraction
    """
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Candidate).where(
            and_(Candidate.id == candidate_id, Candidate.tenant_id == tenant_id)
        )
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المرشح غير موجود",
        )

    # Get job criteria from job posting or use default
    criteria = job_criteria
    if not criteria and candidate.job_posting_id:
        job_result = await db.execute(
            select(JobPosting).where(JobPosting.id == candidate.job_posting_id)
        )
        job = job_result.scalar_one_or_none()
        if job and job.criteria:
            criteria = job.criteria
        elif job:
            criteria = [
                {"title": "خبرة ذات صلة", "keywords": "خبرة,سنوات,سنية", "weight": 30, "required": True},
                {"title": "مهارات تقنية", "keywords": "برمجة,تقنية,تقنيات,programming", "weight": 30, "required": False},
                {"title": "التعليم", "keywords": "بكالوريوس,ماجستير,دكتوراه,جامعة", "weight": 20, "required": False},
            ]

    if not criteria:
        criteria = [
            {"title": "خبرة ذات صلة", "keywords": "خبرة,سنوات,سنية", "weight": 50, "required": True},
        ]

    # Score the CV
    normalized_text = normalize_text(candidate.cv_text or "")
    total_weight = sum(c["weight"] for c in criteria)
    total_score = 0

    criteria_results = []
    for criterion in criteria:
        keywords = criterion["keywords"].lower().split(",")
        matched = sum(1 for kw in keywords if kw.strip() in normalized_text)
        score = (matched / len(keywords)) * 100 if keywords else 0
        total_score += score * criterion["weight"] / total_weight

        criteria_results.append({
            "criterion": criterion["title"],
            "score": round(score, 1),
            "weight": criterion["weight"],
            "matched_keywords": [kw for kw in keywords if kw.strip() in normalized_text],
            "missing_keywords": [kw for kw in keywords if kw.strip() not in normalized_text],
            "required": criterion.get("required", False),
        })

    avg_score = round(total_score, 1)

    # LLM extraction (if available)
    llm_extraction = None
    if candidate.cv_text and os.environ.get("OPENAI_API_KEY"):
        try:
            from app.services.llm_service import extract_cv_facts
            llm_extraction = await extract_cv_facts(candidate.cv_text, [c["title"] for c in criteria])
        except Exception:
            pass

    # Update candidate with scores
    candidate.cv_score = avg_score
    candidate.cv_analysis = {
        "score": avg_score,
        "criteria_results": criteria_results,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
    candidate.llm_extraction = llm_extraction

    # Update stage based on score
    if avg_score >= 70:
        candidate.stage = "screening"
    elif avg_score >= 40:
        candidate.stage = "screening"
    else:
        candidate.stage = "rejected"

    await db.commit()

    return {
        "candidate_id": candidate.id,
        "cv_score": avg_score,
        "stage": candidate.stage,
        "criteria_results": criteria_results,
        "llm_extraction": llm_extraction,
    }


# -----------------------------------------------------------------------------
# AI Interview
# -----------------------------------------------------------------------------
@router.post("/candidates/{candidate_id}/interview/invite")
async def invite_ai_interview(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin", "hr_manager")),
):
    """
    إرسال دعوة لمقابلة AI للمرشح
    يتم إنشاء مقابلة غير محددة الوقت يمكن للمرشح إكمالها في أي وقت
    """
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(Candidate).where(
            and_(Candidate.id == candidate_id, Candidate.tenant_id == tenant_id)
        ).options(selectinload(Candidate.job_posting))
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المرشح غير موجود",
        )

    if candidate.stage not in ("screening", "interview"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="هذا المرشح ليس في مرحلة المقابلة",
        )

    # Check if interview already exists
    int_result = await db.execute(
        select(AIInterview).where(AIInterview.candidate_id == candidate_id)
    )
    if int_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="المقابلة موجودة بالفعل",
        )

    # Create interview with generated questions
    job = candidate.job_posting
    questions = generate_interview_questions(job, candidate)

    interview = AIInterview(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        job_posting_id=candidate.job_posting_id,
        questions=questions,
        status="pending",
        invitation_sent_at=datetime.now(timezone.utc),
    )
    db.add(interview)
    await db.commit()

    # In production: send email/SMS to candidate with interview link
    # interview_url = f"/interview/{interview.id}"

    return {
        "message": "تم إرسال دعوة المقابلة",
        "interview_id": interview.id,
        "questions_count": len(questions),
        "expires_in_hours": 48,
    }


@router.get("/candidates/{candidate_id}/interview")
async def get_interview(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """الحصول على بيانات المقابلة"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(AIInterview)
        .where(and_(AIInterview.candidate_id == candidate_id, AIInterview.tenant_id == tenant_id))
        .options(selectinload(AIInterview.candidate))
    )
    interview = result.scalar_one_or_none()

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المقابلة غير موجودة",
        )

    return {
        "interview_id": interview.id,
        "candidate_id": interview.candidate_id,
        "candidate_name": f"{interview.candidate.first_name} {interview.candidate.last_name}",
        "status": interview.status,
        "questions": interview.questions,
        "answers": interview.answers,
        "evaluation": interview.evaluation,
        "score": interview.score,
        "started_at": interview.started_at,
        "completed_at": interview.completed_at,
        "created_at": interview.created_at,
    }


@router.post("/interviews/{interview_id}/complete")
async def complete_interview(
    interview_id: str,
    answers: List[dict],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    إرسال إجابات المرشح للمقابلة
    يتم تقييم الإجابات تلقائياً بالـ AI
    """
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(AIInterview).where(
            and_(AIInterview.id == interview_id, AIInterview.tenant_id == tenant_id)
        ).options(selectinload(AIInterview.candidate))
    )
    interview = result.scalar_one_or_none()

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المقابلة غير موجودة",
        )

    interview.answers = answers
    interview.status = "completed"
    interview.completed_at = datetime.now(timezone.utc)

    # Evaluate answers (in production: use AI model)
    evaluation = evaluate_interview_answers(interview.questions, answers)
    interview.evaluation = evaluation
    interview.score = evaluation.get("overall_score", 0)

    await db.commit()

    return {
        "message": "تم تقييم المقابلة",
        "interview_id": interview.id,
        "score": interview.score,
        "evaluation": evaluation,
    }


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    if not text:
        return ""
    return text.lower().strip()


def generate_interview_questions(job: Optional[JobPosting], candidate: Candidate) -> List[dict]:
    """Generate interview questions based on job and candidate."""
    questions = [
        {
            "id": uuid.uuid4().hex,
            "question": "رحب بك؟ تخبرني عن نفسك وبخبرتك العمل في هذا المجال؟",
            "type": "text",
            "max_time_minutes": 3,
            "role": "introduction",
        },
        {
            "id": uuid.uuid4().hex,
            "question": "ما هي أبرز الإنجازات في مسيرتك المهنية؟",
            "type": "text",
            "max_time_minutes": 3,
            "role": "experience",
        },
    ]

    if job and job.criteria:
        for criterion in job.criteria[:3]:
            questions.append({
                "id": uuid.uuid4().hex,
                "question": f"السؤال عن: {criterion['title']} - {criterion['keywords']}",
                "type": "text",
                "max_time_minutes": 3,
                "role": "skills",
            })

    if job and job.requirements:
        questions.append({
            "id": uuid.uuid4().hex,
            "question": f"ما هي أهم التحديات التي واجهتها في عملك السابق وكيف تغلبت عليها؟",
            "type": "text",
            "max_time_minutes": 3,
            "role": "problem_solving",
        })

    if job and job.salary_min:
        questions.append({
            "id": uuid.uuid4().hex,
            "question": "ما هي توقعاتك للراتب؟",
            "type": "text",
            "max_time_minutes": 1,
            "role": "salary",
        })

    questions.append({
        "id": uuid.uuid4().hex,
        "question": "لماذا ترغب في الانضمام إلى شركتنا؟",
        "type": "text",
        "max_time_minutes": 2,
        "role": "motivation",
    })

    return questions


def evaluate_interview_answers(questions: List[dict], answers: List[dict]) -> dict:
    """Evaluate interview answers (placeholder for AI evaluation)."""
    scores = []
    details = []

    for i, (q, a) in enumerate(zip(questions, answers)):
        answer_text = a.get("answer", "")
        length_score = min(len(answer_text.split()) / 50, 1.0) * 30  # Content length
        relevance_score = 40  # Placeholder - would be AI evaluated
        clarity_score = 30  # Placeholder

        score = round(length_score + relevance_score + clarity_score, 1)
        scores.append(score)

        details.append({
            "question_id": q["id"],
            "question": q["question"],
            "score": score,
            "max_score": 100,
        })

    overall = round(sum(scores) / len(scores), 1) if scores else 0

    return {
        "overall_score": overall,
        "by_question": details,
        "total_questions": len(questions),
        "answered_questions": len(answers),
    }
