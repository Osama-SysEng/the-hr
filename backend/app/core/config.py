"""
The H.R - Configuration Settings
منصة إدارة الموارد البشرية المتكاملة
"""

from functools import lrufunc
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "The H.R"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://hr_user:hr_password@localhost:5432/thehr"
    DATABASE_SSL_MODE: str = "prefer"

    # Redis (for Celery + caching)
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production-thehr"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # AI / LLM
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    CV_SCREENING_MODEL: str = "gpt-4o-mini"
    AI_INTERVIEW_MODEL: str = "gemini-1.5-pro"

    # Face Recognition
    FACE_RECOGNITION_TOLERANCE: float = 0.6

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # SMS
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Biometric (ZKTeco)
    ZKTEco_SDK_PATH: str = "/usr/lib/zkteco"

    # Storage
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    # Multi-tenant
    DEFAULT_TENANT_ID: str = "default"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def get_settings() -> Settings:
    return settings
