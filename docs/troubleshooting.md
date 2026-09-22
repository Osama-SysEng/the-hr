# Troubleshooting

## مشاكل شائعة
1. **لم يعمل alembic**: تأكد من DATABASE_URL وأدوات PostgreSQL
2. **FastAPI لا يبدأ**: تحقق من REDIS_URL و أضف --reload للتجربة
3. **الواجهة لا تتصل بالـ API**: تحقق من VITE_API_URL في الـ frontend
4. **البصمة لا تعمل**: تأكد من وجود face_recognition library و OpenCV
5. **البريد لا يُرسل**: تحقق من SMTP settings و التحقق من حسابك

## الحلول
- `alembic downgrade -1` لإلغاء آخر migration
- `docker-compose down` ثم `docker-compose up -d` لإعادة تشغيل كل شيء
- تحقق من logs: `docker-compose logs backend`
