from fastapi import APIRouter
from app.api.v1.endpoints import trends, scripts, videos, users, websocket

api_v1_router = APIRouter()

# Include endpoint sub-routers
api_v1_router.include_router(trends.router)
api_v1_router.include_router(scripts.router)
api_v1_router.include_router(videos.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(websocket.router)
