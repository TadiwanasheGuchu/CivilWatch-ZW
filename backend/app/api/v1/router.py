from fastapi import APIRouter

from app.api.v1 import auth, councils, geo, health, issues, notifications, operations, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(geo.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(councils.router)
api_router.include_router(issues.categories_router)
api_router.include_router(issues.router)
api_router.include_router(operations.router)
api_router.include_router(notifications.router)
