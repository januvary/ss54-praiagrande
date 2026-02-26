from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    MAGIC_LINK_EXPIRE_MINUTES: int = 15

    # Frontend
    FRONTEND_URL: str = "http://localhost:8080"

    # Email
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAILS_FROM_EMAIL: EmailStr
    EMAILS_FROM_NAME: str = "SS-54 Assistência Farmacêutica de Praia Grande"
    DRS_RENOVACAO_EMAIL: EmailStr
    DRS_SOLICITACAO_EMAIL: EmailStr

    # Application
    APP_NAME: str = "SS-54"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:8080"

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB

    # Admin Panel
    ADMIN_ALLOWED_IPS: str = "127.0.0.1,::1"  # IPv4 and IPv6 localhost, supports CIDR
    ADMIN_PASSWORD_HASH: str = ""  # bcrypt hash of admin password
    ADMIN_SESSION_DAYS: int = 7  # Days until admin session expires

    # Server
    # Default to 0.0.0.0 for development, use env var HOST in production
    HOST: str = "0.0.0.0"  # nosec: B104
    PORT: int = 8000

    # Data Retention (LGPD)
    DATA_RETENTION_YEARS: int = 5  # Years to retain process data after completion
    DATA_RETENTION_ENABLED: bool = True  # Enable automatic data retention cleanup

    # Scheduler
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_TIMEZONE: str = "America/Sao_Paulo"
    BATCH_SEND_HOUR: int = 9
    BATCH_SEND_ENABLED: bool = True
    DRS_FOLLOWUP_HOUR: int = 10
    DRS_FOLLOWUP_ENABLED: bool = True
    AUTO_EXPIRE_HOUR: int = 8
    AUTO_EXPIRE_ENABLED: bool = True

    # Authorization Expiry
    AUTH_EXPIRY_DAYS: int = 180  # Days until authorization expires
    AUTH_EXPIRY_WARNING_DAYS: int = 30  # Days before expiry to show warning
    NUTRICAO_EXPIRY_DAYS: int = 120  # Days until nutrição authorization expires

    # Scheduler Business Rules
    BATCH_INTERVAL_DAYS: int = 14  # Days between automatic batch sends
    DRS_DEADLINE_DAYS: List[int] = [30, 60]  # DRS follow-up deadlines in days
    BATCH_ANCHOR_DATE: str = "2026-02-13"  # YYYY-MM-DD format

    # Storage (NFS/Remote)
    STORAGE_HEALTHCHECK_INTERVAL: int = 60  # Seconds between storage health checks
    STORAGE_RETRY_MAX_ATTEMPTS: int = 3  # Max retries for file operations
    STORAGE_RETRY_DELAY: float = 0.5  # Initial retry delay in seconds
    STORAGE_STARTUP_REQUIRED: bool = True  # Fail startup if storage unavailable

    LOW_MEMORY_MODE: bool = True  # Enable reduced pool sizes and aggressive GC

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )


settings = Settings()  # type: ignore
