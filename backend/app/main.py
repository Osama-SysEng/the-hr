"""
The H.R - Main FastAPI Application
Entry point for The H.R Backend API
"""

import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from app.api import api_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.logging_utils import get_logger, new_request_id, request_id_ctx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

logger = get_logger("app.main")
access_logger = get_logger("http.access")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: Close database
    await close_db()


# -----------------------------------------------------------------------------
# Create FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    description="""The H.R - AI-Powered Human Resources Operating System

منصة إدارة الموارد البشرية المتكاملة والأوتوماتيكية

**الموديولات:**
- ✅ Smart Attendance System (4-layer biometric verification)
- ✅ Payroll Engine (automated Egyptian payroll)
- ✅ AI Recruitment Engine (500+ CVs in 5 minutes)
- ✅ Supply Chain Management
- ✅ AI Analytics & Predictions
- ✅ Employee Self-Service Portal

**التقنيات:**
- FastAPI (Python 3.11+)
- PostgreSQL + SQLAlchemy
- Redis + Celery
- React 18 + TypeScript + Tailwind CSS
- JWT + RBAC Authentication""",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Request ID + Access Log (single line per request)
# -----------------------------------------------------------------------------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or new_request_id()
    request_id_ctx.set(request_id)
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    access_logger.info(
        f"access: {request.method} {request.url.path} -> {response.status_code}",
        extra={"fields": {
            "event": "http.access",
            "method": request.method,
            "route": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        }},
    )
    return response


# -----------------------------------------------------------------------------
# Rate Limiting (sliding window per IP+path, /health exempt)
# -----------------------------------------------------------------------------
def _rate_limit_per_minute() -> int:
    try:
        value = int(os.getenv("RATE_LIMIT_PER_MINUTE", "600"))
    except ValueError:
        value = 600
    return max(1, min(value, 6000))


_RATE_LIMIT = _rate_limit_per_minute()
_rate_hits: dict = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path != "/health":
        now = time.monotonic()
        window_start = now - 60.0
        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"
        recent = [t for t in _rate_hits[key] if t > window_start]
        _rate_hits[key] = recent
        if len(recent) >= _RATE_LIMIT:
            return JSONResponse(
                {"success": False, "error": {"code": 429, "message": "rate limit exceeded"}}, status_code=429
            )
        recent.append(now)
    return await call_next(request)


# -----------------------------------------------------------------------------
# Exception Handlers
# -----------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled exception", extra={"fields": {"event": "http.error", "route": request.url.path}})
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "حدث خطأ داخلي في الخادم",
            },
        },
    )


# -----------------------------------------------------------------------------
# Include API Routes
# -----------------------------------------------------------------------------
app.include_router(api_router)


# -----------------------------------------------------------------------------
# Root Endpoint
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    """The H.R Root Endpoint"""
    return """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The H.R - AI HR Operating System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #07111f 0%, #0a1929 50%, #07111f 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
        }
        .container {
            text-align: center;
            max-width: 800px;
            padding: 40px;
        }
        .logo {
            width: 120px;
            height: 120px;
            margin: 0 auto 30px;
            background: linear-gradient(135deg, #00b4d8, #0077b6);
            border-radius: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            font-weight: bold;
            box-shadow: 0 0 40px rgba(0, 180, 216, 0.3);
        }
        h1 {
            font-size: 48px;
            font-weight: 800;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00b4d8, #48cae4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle {
            font-size: 18px;
            color: #94a3b8;
            margin-bottom: 40px;
        }
        .modules {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 40px;
        }
        .module {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        .module h3 {
            font-size: 14px;
            color: #00b4d8;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .module p {
            font-size: 12px;
            color: #64748b;
            line-height: 1.4;
        }
        .tech-stack {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            margin-bottom: 30px;
        }
        .tech {
            background: rgba(0, 180, 216, 0.1);
            border: 1px solid rgba(0, 180, 216, 0.3);
            border-radius: 20px;
            padding: 8px 16px;
            font-size: 12px;
            color: #48cae4;
        }
        .endpoints {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 16px;
            padding: 20px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #48cae4;
            text-align: left;
        }
        .endpoints h3 {
            color: #fff;
            margin-bottom: 15px;
            font-size: 14px;
        }
        .endpoint {
            padding: 5px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .method {
            display: inline-block;
            width: 60px;
            font-weight: bold;
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 4px;
            color: #fff;
            margin-right: 10px;
        }
        .get { background: #10b981; }
        .post { background: #3b82f6; }
        .put { background: #f59e0b; }
        .delete { background: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">HR</div>
        <h1>The H.R</h1>
        <p class="subtitle">AI-Powered Human Resources Operating System</p>
        
        <div class="modules">
            <div class="module">
                <h3>Smart Attendance</h3>
                <p>4-layer biometric verification: fingerprint, GPS, camera, face recognition</p>
            </div>
            <div class="module">
                <h3>Payroll Engine</h3>
                <p>Automated Egyptian payroll with insurance & tax calculations</p>
            </div>
            <div class="module">
                <h3>AI Recruitment</h3>
                <p>Screen 500+ CVs in minutes | AI interviews in Arabic</p>
            </div>
            <div class="module">
                <h3>Supply Chain</h3>
                <p>Inventory, purchasing, suppliers management</p>
            </div>
            <div class="module">
                <h3>AI Analytics</h3>
                <p>Turnover prediction, payroll forecast, dashboards</p>
            </div>
            <div class="module">
                <h3>Employee Portal</h3>
                <p>Self-service: attendance, leave, payslips, documents</p>
            </div>
        </div>

        <div class="tech-stack">
            <span class="tech">FastAPI</span>
            <span class="tech">PostgreSQL</span>
            <span class="tech">SQLAlchemy</span>
            <span class="tech">Redis + Celery</span>
            <span class="tech">React 18 + TypeScript</span>
            <span class="tech">Tailwind CSS 4</span>
            <span class="tech">JWT + RBAC</span>
            <span class="tech">OpenAI + Gemini</span>
        </div>

        <div class="endpoints">
            <h3>📚 API Endpoints:</h3>
            <div class="endpoint"><span class="method get">GET</span> /api/v1/auth/me</div>
            <div class="endpoint"><span class="method post">POST</span> /api/v1/auth/login</div>
            <div class="endpoint"><span class="method get">GET</span> /api/v1/employees</div>
            <div class="endpoint"><span class="method post">POST</span> /api/v1/employees</div>
            <div class="endpoint"><span class="method post">POST</span> /api/v1/attendance/clock-in</div>
            <div class="endpoint"><span class="method post">POST</span> /api/v1/attendance/clock-out</div>
            <div class="endpoint"><span class="method post">POST</span> /api/v1/payroll/calculate</div>
            <div class="endpoint"><span class="method get">GET</span> /api/v1/payroll/{id}</div>
            <div class="endpoint"><span class="method get">GET</span> /api/v1/recruitment/jobs</div>
            <div class="endpoint"><span class="method post">POST</span> /api/v1/recruitment/candidates</div>
            <div class="endpoint"><span class="method post">POST</span> /api/v1/recruitment/candidates/{id}/screen</div>
            <div class="endpoint"><span class="method get">GET</span> /api/v1/inventory/products</div>
            <div class="endpoint"><span class="method post">POST</span> /api/v1/inventory/purchase-orders</div>
            <div class="endpoint"><span class="method get">GET</span> /api/v1/analytics/dashboard</div>
            <div class="endpoint"><span class="method get">GET</span> /api/v1/dashboard/overview</div>
            <div class="endpoint" style="margin-top:15px;color:#94a3b8;">📖 Documentation: <a href="/docs" style="color:#00b4d8;">/docs</a> | 📘 ReDoc: <a href="/redoc" style="color:#00b4d8;">/redoc</a></div>
        </div>

        <p style="color:#475569; font-size: 12px; margin-top: 30px;">
            Made with ❤️ for Egypt | Built for MENA | Built for anyone
        </p>
    </div>
</body>
</html>
    """


# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# -----------------------------------------------------------------------------
# OpenAPI Customization
# -----------------------------------------------------------------------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add Arabic summary
    openapi_schema["info"]["x-summary-ar"] = "منصة إدارة الموارد البشرية المتكاملة"

    # Tag descriptions
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "تسجيل الدخول، التسجيل، وإدارة الجلسات",
        },
        {
            "name": "Employees",
            "description": "إدارة الموظفين: إضافة، تعديل، حذف، بحث",
        },
        {
            "name": "Attendance",
            "description": "نظام الحضور والانصراف: تسجيل الدخول والخروج، التقارير",
        },
        {
            "name": "Payroll",
            "description": "نظام الرواتب: الحساب التلقائي، الكشوف، الدفع",
        },
        {
            "name": "Recruitment",
            "description": "نظام التوظيف: وظائف، مرشحين، فحص CVs بالذكاء الاصطناعي",
        },
        {
            "name": "Inventory",
            "description": "إدارة المخزن: منتجات، حركات، أوامر شراء، موردين",
        },
        {
            "name": "Dashboard",
            "description": "لوحة التحكم الموحدة مع KPIs والإحصائيات",
        },
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# -----------------------------------------------------------------------------
# Run with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)  # noqa: S104 -- container entrypoint bind
