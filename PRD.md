# PRD — The-HR (AI-Powered HR Operating System)
## 1. نظرة عامة
- منصة SaaS للموارد البشرية: حضور، رواتب مصرية، توظيف AI، مخزون، إجازات/سلف، تحليلات.
- Backend: FastAPI + PostgreSQL + Redis/Celery. Base URL: `/api/v1`.
- Frontend: React + TypeScript + Tailwind. Docs: `/docs` و`/redoc`.
## 2. المستخدمون
1. super_admin — إعداد الشركة والأقسام.
2. admin/hr_manager — توظيف وحضور وإجازات.
3. manager — اعتماد طلبات فريقه.
4. employee — بوابة ذاتية (حضوري، قسائمي، إجازاتي).
5. accountant — تشغيل الرواتب واعتمادها.
## 3. الميزات الأساسية (قابلة للاختبار)
1. تسجيل مستخدم جديد عبر `/auth/register`.
2. تسجيل دخول JWT عبر `/auth/login` + بياناتي `/auth/me`.
3. تعديل الملف الشخصي وتغيير كلمة المرور ونسيانها.
4. CRUD موظفين + بحث + استيراد bulk.
5. Clock-in/out + سجلات + تقرير يومي/فترة.
6. حساب راتب + اعتماد + دفع + إرسال + payslip + إحصائيات + calculate-all.
7. طلب إجازة + اعتماد/رفض + رصيد الإجازات.
8. طلب سلفة/قرض + اعتماد/رفض.
9. وظائف CRUD + إغلاق + مرشحون + نقل مرحلة + فحص AI + دعوة/إتمام interview.
10. منتجات CRUD + حركات مخزون + موردون + أوامر شراء + ملخص تقرير.
11. تحليلات (حضور/توظيف/رواتب/سلسلة إمداد) + لوحات حسب الدور.
12. إعدادات شركة/أقسام + قائمة موظفين مبسطة.
## 4. الـAPI endpoints الحقيقية (من الكود فقط)
- `POST /api/v1/auth/login` / `POST /api/v1/auth/register`
- `GET /api/v1/auth/me` / `PUT /api/v1/auth/me`
- `PUT /api/v1/auth/password` / `POST /api/v1/auth/forgot-password`
- `GET /api/v1/employees` / `POST /api/v1/employees` / `GET /api/v1/employees/search` / `POST /api/v1/employees/bulk`
- `GET/PUT/DELETE /api/v1/employees/{employee_id}`
- `POST /api/v1/attendance/clock-in` / `POST /api/v1/attendance/clock-out`
- `GET /api/v1/attendance/today` / `GET /api/v1/attendance/records` / `GET /api/v1/attendance/report/daily` / `POST /api/v1/attendance/report/period`
- `POST /api/v1/payroll/calculate` / `POST /api/v1/payroll/calculate-all` / `GET /api/v1/payroll` / `GET /api/v1/payroll/statistics`
- `GET /api/v1/payroll/{payroll_id}` / `GET /api/v1/payroll/{payroll_id}/payslip` / `POST /api/v1/payroll/{payroll_id}/approve|pay|send`
- `GET/POST /api/v1/hr/leaves` / `PUT /api/v1/hr/leaves/{leave_id}/approve|reject` / `GET /api/v1/hr/leaves/balance`
- `GET/POST /api/v1/hr/loans` / `PUT /api/v1/hr/loans/{loan_id}/approve|reject`
- `GET/POST /api/v1/recruitment/jobs` / `GET/PUT /api/v1/recruitment/jobs/{job_id}` / `POST /api/v1/recruitment/jobs/{job_id}/close`
- `GET/POST /api/v1/recruitment/candidates` / `GET /api/v1/recruitment/candidates/{candidate_id}` / `PUT .../stage` / `POST .../screen` / `POST .../interview/invite` / `GET .../interview` / `POST /api/v1/recruitment/interviews/{interview_id}/complete`
- `GET/POST /api/v1/inventory/products` / `PUT /api/v1/inventory/products/{product_id}` / `POST /api/v1/inventory/movements` / `GET/POST /api/v1/inventory/suppliers` / `GET/POST /api/v1/inventory/purchase-orders` / `GET /api/v1/inventory/report/summary`
- `GET /api/v1/analytics/attendance|recruitment|payroll|supply-chain` / `GET /api/v1/dashboard/*` / `GET/PUT /api/v1/settings/company` / `GET /api/v1/settings/departments` / `GET /health`
## 5. بيانات الدخول/الإعداد للاختبار
- انسخ `backend/.env.example` إلى `backend/.env`.
- عيّن `DATABASE_URL` + `REDIS_URL` + `SECRET_KEY` (32+ حرفًا).
- بذرة README: `admin@thehr.com` / `Admin@123`.
- تشغيل: `uvicorn app.main:app --reload` (8000). اختبارات: `pytest app/tests/ -v`.
## 6. خارج النطاق (mocked/simulated — صراحة)
- بصمة/GPS/CCTV/Face+liveness تحتاج أجهزة ومكتبات حقيقية.
- مفاتيح `OPENAI`/`GEMINI`/`AISA` و`Twilio`/`SMTP` غير موجودة افتراضيًا — تُختبر المسارات فقط.
- حسابات الضرائب/التأمينات المصرية تُختبر حسابيًا لا ضد جهة حكومية.
- لا بوابة دفع حقيقية ولا نشر رواتب بنكي.
