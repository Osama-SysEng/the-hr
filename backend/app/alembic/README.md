"""
The H.R - Alembic Migrations

استخدام Alembic لإدارة تغييرات قاعدة البيانات:

الCommands الأساسية:
    # تحديث قاعدة البيانات لأحدث نسخة
    alembic upgrade head

    # إعادة تعيين قاعدة البيانات من الصفر
    alembic downgrade -1

    # عرض التاريخ
    alembic history

    # عرض الفرق بين当前和头部
    alembic current

    # إنشاء نسخة احتياطية قبل التحديث
    alembic upgrade -1

# إنشاء migration جديد (عندما تتغير النماذج)
    alembic revision --autogenerate -m "description"

ملاحظات:
    - الإعدادات من app/core/config.py
    - قاعدة البيانات: PostgreSQL + asyncpg
    - جميع التحولات transactional
    - Migration IDs: YYYY-MM-DD-description
"""
