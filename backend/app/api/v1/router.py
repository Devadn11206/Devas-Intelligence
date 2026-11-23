from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.orgs import router as orgs_router
from app.api.v1.admin import router as admin_router
from app.api.v1.admin_ingestion import router as admin_ingestion_router
from app.api.v1.intel import router as intel_router
from app.api.v1.search import router as search_router
from app.api.v1.trends import router as trends_router
from app.api.v1.reports import router as reports_router
from app.api.v1.agents import router as agents_router

router = APIRouter(prefix="/v1")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(orgs_router)
router.include_router(admin_router)
router.include_router(admin_ingestion_router)
router.include_router(intel_router)
router.include_router(search_router)
router.include_router(trends_router)
router.include_router(reports_router)
router.include_router(agents_router)
