"""Application configuration from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.paths import find_project_root, resolve_from_root

_REPO_ROOT = find_project_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            _REPO_ROOT / ".env",
            _REPO_ROOT / "api" / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Alma Lead Intake API"
    debug: bool = False

    database_url: str = "postgresql://alma:alma@localhost:5432/alma"
    # Relative to repo root unless absolute (see resolve_from_root).
    uploads_dir: str = "storage/uploads"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    cors_origins: list[str] = ["http://localhost:3000"]

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    webapp_url: str = "http://localhost:3000"

    enable_llm_enrichment: bool = False

    verification_token_ttl_hours: int = 24

    # L1b — reclaim a stuck pending row when used_at is set but lead_id is still null.
    verification_processing_stale_minutes: int = 5

    # F2.5 — days after archive before resume purge job may delete files (job TBD).
    resume_retention_days: int = 365

    # Demo / seed credentials — override per-env via env vars in production.
    demo_admin_password: str = "admin123"
    demo_attorney_password: str = "attorney123"
    demo_intake_password: str = "intake123"
    demo_readonly_password: str = "readonly123"
    # Set to true to skip the startup seed (tests bypass via patched SessionLocal).
    disable_startup_seed: bool = False

    # Public form abuse protection — POST /api/v1/leads/verification-requests
    rate_limit_enabled: bool = True
    verification_request_rate_limit: str = "5/minute"

    @model_validator(mode="after")
    def _resolve_uploads_dir(self) -> Self:
        resolved = resolve_from_root(self.uploads_dir, root=_REPO_ROOT)
        object.__setattr__(self, "uploads_dir", str(resolved))
        return self

    @property
    def project_root(self) -> Path:
        return _REPO_ROOT


settings = Settings()
