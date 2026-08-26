from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from . import __version__
from .config import get_settings
from .detection import get_detector
from .keys import get_key_provider
from .logging import configure_logging
from .middleware import BodyLimitMiddleware, SecurityMiddleware
from .policies import get_policy_registry
from .routes import router

settings = get_settings()
configure_logging(settings.log_level)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail startup if required controls cannot initialize.
    await asyncio.to_thread(get_key_provider)
    await asyncio.to_thread(get_policy_registry)
    detector = await asyncio.to_thread(get_detector)
    if settings.fail_closed and not detector.healthy:
        raise RuntimeError("Contextual privacy detector unavailable")
    log.info(
        "control_plane_started",
        version=__version__,
        environment=settings.environment,
        key_provider=settings.key_provider,
        fail_closed=settings.fail_closed,
    )
    yield
    log.info("control_plane_stopped")


app = FastAPI(
    title="AirShield Privacy Control Plane",
    version=__version__,
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["authorization", "content-type", "idempotency-key", "x-correlation-id"],
)
app.add_middleware(SecurityMiddleware)
app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_text_bytes + 16_384)
app.include_router(router)
app.mount("/internal/metrics", make_asgi_app())


@app.get("/")
async def root():
    return {
        "service": "airshield-control-plane",
        "version": __version__,
        "documentation": "disabled in production" if settings.environment == "production" else "/docs",
    }
