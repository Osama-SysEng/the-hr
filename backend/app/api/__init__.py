"""
The H.R - API Routers
FastAPI routers for all HR modules
"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.employees import router as employees_router
from app.api.attendance import router as attendance_router
from app.api.payroll import router as payroll_router
from app.api.leave import router as leave_router
from app.api.recruitment import router as recruitment_router
from app.api.inventory import router as inventory_router
from app.api.analytics import router as analytics_router
from app.api.settings import router as settings_router
from app.api.dashboard import dashboard_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(employees_router)
api_router.include_router(attendance_router)
api_router.include_router(payroll_router)
api_router.include_router(leave_router)
api_router.include_router(recruitment_router)
api_router.include_router(inventory_router)
api_router.include_router(analytics_router)
api_router.include_router(settings_router)
api_router.include_router(dashboard_router)


__all__ = [
    "api_router",
]
