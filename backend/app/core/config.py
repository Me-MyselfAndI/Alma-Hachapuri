"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Alma Lead Intake API"
    debug: bool = False

    database_url: str = "postgresql://alma:alma@localhost:5432/alma"
    uploads_dir: str = "uploads"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    cors_origins: list[str] = ["http://localhost:3000"]

    smtp_host: str = "localhost"
    smtp_port: int = 1025

    enable_llm_enrichment: bool = False


settings = Settings()
