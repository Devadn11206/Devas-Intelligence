from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import get_settings
from app.core.logging import configure_logging, RequestIDMiddleware, get_logger
from app.core.exceptions import register_exception_handlers
from app.core.metrics import PrometheusMiddleware, get_metrics_response
from app.api.v1.router import router as v1_router
import app.modules.ingestion.adapters  # Registers all ingestion adapters (arxiv, github, huggingface, semantic_scholar, rss)

settings = get_settings()
configure_logging(environment=settings.ENVIRONMENT, debug=settings.DEBUG)
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("application_startup", app_name=settings.APP_NAME, env=settings.ENVIRONMENT)
    yield
    logger.info("application_shutdown", app_name=settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="DEVA Intelligence - AI-powered technology intelligence SaaS platform",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Exception handlers
register_exception_handlers(app)

# Middlewares
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# API Router Registration
app.include_router(v1_router, prefix="/api")


@app.get("/metrics", include_in_schema=False)
def metrics_endpoint():
    return get_metrics_response()


# Serve Frontend SPA directly on port 8000
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    # Mount assets (CSS, JS, media)
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Fallback to index.html for all non-API SPA routes (React Router)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Allow /docs or /redoc if enabled
        if full_path in ("docs", "redoc", "openapi.json"):
            return None
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
            "docs": "/docs",
        }
