"""FastAPI application entrypoint.

Wires all domain routers and runs the demo-account seeder on startup.
Lead-scoped sub-routers (resume, emails, state-history) have no internal
prefix — we mount them under ``/api/v1/leads/{lead_id}/…`` so the lead-id path
parameter is declared exactly once.

Startup seed: ``SeedService.seed_demo_accounts`` is idempotent and only logs
credentials on first insert. It is wrapped in a try/except so a failed DB
connection (e.g. running tests with a patched ``SessionLocal``) doesn't
prevent the app from booting.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import SessionLocal
from src.domains.account.router import accounts_router, auth_router
from src.domains.account.service import SeedService
from src.domains.email.router import emails_router, lead_emails_router
from src.domains.lead.router import router as lead_router
from src.domains.prospect.router import router as prospect_router
from src.domains.resume_file.router import router as resume_router
from src.domains.state_history.router import router as state_history_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run idempotent demo-account seed on startup; no shutdown hook needed."""

    if not settings.disable_startup_seed:
        try:
            db = SessionLocal()
            try:
                SeedService.seed_demo_accounts(db)
            finally:
                db.close()
        except Exception:  # pragma: no cover - exercised via integration only
            logger.exception("Demo-account seed failed; continuing startup")
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(prospect_router)
app.include_router(lead_router)
app.include_router(emails_router)
app.include_router(lead_emails_router)
# Lead-scoped sub-routers: mount with lead-id path param (no internal prefix).
app.include_router(resume_router, prefix="/api/v1/leads/{lead_id}/resume")
app.include_router(
    state_history_router, prefix="/api/v1/leads/{lead_id}/state-history"
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Alma Lead Intake API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
