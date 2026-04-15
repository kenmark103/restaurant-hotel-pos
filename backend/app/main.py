import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.event_bus import bus

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan  (replaces deprecated @app.on_event)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:
      1. Register all domain event handlers on the singleton bus.
      2. Configure payment providers (from env vars).
      3. (Future) start background task workers.

    Shutdown:
      4. Graceful cleanup.
    """
    # ── 1. Wire event bus ────────────────────────────────────────────────────
    from app.core.listeners import register_all_listeners
    register_all_listeners(bus)
    logger.info("Event bus listeners registered.")

    # ── 2. Payment providers ─────────────────────────────────────────────────
    # Providers are registered inside listeners._configure_payment_providers()
    # We call it here with a factory function so it can get a fresh service
    # instance. For MVP (record_only) this is a no-op.
    from app.core.listeners import _configure_payment_providers
    from app.services.payment_service import PaymentService

    def _make_payment_service():
        # A lightweight singleton-ish factory; no DB needed for provider registration
        from unittest.mock import MagicMock
        return PaymentService(db=MagicMock(), current_user=None, event_bus=bus)

    _configure_payment_providers(_make_payment_service)

    yield  # ── Application runs ──────────────────────────────────────────────

    logger.info("Application shutdown.")


# ─────────────────────────────────────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Restaurant POS API",
        version="2.0.0",
        description="Production-grade POS & hospitality management system.",
        lifespan=lifespan,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Static files (PDF receipts, station tickets) ─────────────────────────
    from pathlib import Path
    pdf_dir = Path("/tmp/print_jobs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/print_jobs", StaticFiles(directory=str(pdf_dir)), name="print_jobs")

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.api.router import api_router
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "version": "2.0.0"}
    
    @app.get("/api/v1/ping")
    async def ping() -> dict[str, str]:
        return {"message": "POS API is running"}

    return app


app = create_app()
