"""API router aggregation."""
from fastapi import APIRouter
from app.api.routers.health import router as health_router
from app.api.routers.offers import router as offers_router
from app.api.routers.admin_tasks import router as admin_router
from app.api.routers.calculator import router as calculator_router
from app.api.routers.matches import router as matches_router
from app.api.routers.instructions import router as instructions_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(offers_router)
api_router.include_router(admin_router)
api_router.include_router(calculator_router)
api_router.include_router(matches_router)
api_router.include_router(instructions_router)

