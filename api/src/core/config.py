"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Alma Lead Intake API"
    debug: bool = False

    database_url: str = "postgresql://alma:alma@localhost:5432/alma"
    uploads_dir: str = "../storage/uploads"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    cors_origins: list[str] = ["http://localhost:3000"]

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    webapp_url: str = "http://localhost:3000"

    enable_llm_enrichment: bool = False

    verification_token_ttl_hours: int = 24
    webapp_url: str = "http://localhost:3000"

    # Demo / seed credentials — override per-env via env vars in production.
    demo_admin_password: str = "admin123"
    demo_attorney_password: str = "attorney123"
    demo_intake_password: str = "intake123"
    demo_readonly_password: str = "readonly123"
    # Set to true to skip the startup seed (tests bypass via patched SessionLocal).
    disable_startup_seed: bool = False


settings = Settings()
