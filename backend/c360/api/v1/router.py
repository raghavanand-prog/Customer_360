from fastapi import APIRouter

from . import analytics, auth, customers, health, pipeline, quality, segments

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(customers.router)
api_router.include_router(segments.router)
api_router.include_router(analytics.router)
api_router.include_router(quality.router)
api_router.include_router(pipeline.router)
