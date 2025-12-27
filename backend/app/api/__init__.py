from fastapi import APIRouter
from app.api import health, finance, sec, ai

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(finance.router, prefix="/finance", tags=["finance"])
router.include_router(sec.router, prefix="/sec", tags=["sec"])
router.include_router(ai.router, prefix="/ai", tags=["ai"])
