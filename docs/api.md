# API Endpoints

## المصادقة
- POST `/api/v1/auth/login` - تسجيل الدخول
- POST `/api/v1/auth/register` - إنشاء مستخدم
- GET `/api/v1/auth/me` - بيانات المستخدم
- PUT `/api/v1/auth/password` - تغيير كلمة المرور

## الموظفين
- GET `/api/v1/employees` - قائمة الموظفين
- GET `/api/v1/employees/{id}` - موظف محدد
- POST `/api/v1/employees` - إنشاء موظف
- PUT `/api/v1/employees/{id}` - تعديل موظف
- DELETE `/api/v1/employees/{id}` - إقالة موظف
- POST `/api/v1/employees/bulk` - استيراد دفعة
- GET `/api/v1/employees/search` - بحث سريع

## الحضور
- POST `/api/v1/attendance/clock-in` - تسجيل دخول
- POST `/api/v1/attendance/clock-out` - تسجيل خروج
- GET `/api/v1/attendance/today` - حضور اليوم
- GET `/api/v1/attendance/records` - سجلات الحضور
- GET `/api/v1/attendance/report/daily` - تقرير يومي
- POST `/api/v1/attendance/report/period` - تقرير فترة

## الرواتب
- POST `/api/v1/payroll/calculate` - حساب راتب
- GET `/api/v1/payroll` - قائمة الرواتب
- GET `/api/v1/payroll/{id}` - راتب محدد
- POST `/api/v1/payroll/{id}/approve` - الموافقة
- POST `/api/v1/payroll/{id}/pay` - تسجيل الدفع
- POST `/api/v1/payroll/{id}/send` - إرسال كشف
- GET `/api/v1/payroll/{id}/payslip` - بيانات كشف
- POST `/api/v1/payroll/calculate-all` - حساب الجميع
- GET `/api/v1/payroll/statistics` - إحصائيات

## التوظيف
- GET `/api/v1/recruitment/jobs` - قائمة الوظائف
- POST `/api/v1/recruitment/jobs` - إنشاء وظيفة
- PUT `/api/v1/recruitment/jobs/{id}` - تعديل
- POST `/api/v1/recruitment/jobs/{id}/close` - إغلاق
- GET `/api/v1/recruitment/candidates` - قائمة المرشحين
- POST `/api/v1/recruitment/candidates` - إضافة مرشح
- POST `/api/v1/recruitment/candidates/{id}/screen` - فحص AI
- POST `/api/v1/recruitment/candidates/{id}/interview/invite` - دعوة مقابلة
- GET `/api/v1/recruitment/candidates/{id}/interview` - بيانات مقابلة
- POST `/api/v1/recruitment/interviews/{id}/complete` - إرسال إجابات

## المخزن
- GET `/api/v1/inventory/products` - قائمة المنتجات
- POST `/api/v1/inventory/products` - إنشاء منتج
- PUT `/api/v1/inventory/products/{id}` - تعديل
- POST `/api/v1/inventory/movements` - حركة مخزن
- GET `/api/v1/inventory/suppliers` - قائمة الموردين
- POST `/api/v1/inventory/suppliers` - إنشاء مورد
- POST `/api/v1/inventory/purchase-orders` - أمر شراء
- GET `/api/v1/inventory/purchase-orders` - قائمة الأوامر
- GET `/api/v1/inventory/purchase-orders/{id}` - تفاصيل
- GET `/api/v1/inventory/report/summary` - تقرير مخزن

## الإجازات والقروض
- GET `/api/v1/hr/leaves` - قائمة الإجازات
- POST `/api/v1/hr/leaves` - طلب إجازة
- PUT `/api/v1/hr/leaves/{id}/approve` - الموافقة
- PUT `/api/v1/hr/leaves/{id}/reject` - الرفض
- GET `/api/v1/hr/leaves/balance` - رصيد الإجازات
- GET `/api/v1/hr/loans` - قائمة القروض
- POST `/api/v1/hr/loans` - طلب قرض
- PUT `/api/v1/hr/loans/{id}/approve` - الموافقة
- PUT `/api/v1/hr/loans/{id}/reject` - الرفض

## التحليلات
- GET `/api/v1/analytics/attendance/analytics` - تحليلات الحضور
- GET `/api/v1/analytics/recruitment/analytics` - تحليلات التوظيف
- GET `/api/v1/analytics/payroll/analytics` - تحليلات الرواتب
- GET `/api/v1/analytics/supply-chain/analytics` - تحليلات المخزن

## لوحة التحكم
- GET `/api/v1/dashboard/admin` - لوحة المشرف
- GET `/api/v1/dashboard/hr` - لوحة HR
- GET `/api/v1/dashboard/manager` - لوحة المدير
- GET `/api/v1/dashboard/employee` - لوحة الموظف

## الإعدادات
- GET `/api/v1/settings/company` - إعدادات الشركة
- PUT `/api/v1/settings/company` - تحديث الإعدادات
- GET `/api/v1/settings/employees/simple-list` - قائمة الموظفين المبسطة
- GET `/api/v1/settings/departments` - قائمة الأقسام
- GET `/api/v1/settings/profile` - الملف الشخصي الكامل
