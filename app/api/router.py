from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.comments import router as comments_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.tickets import router as tickets_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.ws import router as ws_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(tickets_router)
api_router.include_router(comments_router)
api_router.include_router(dashboard_router)
api_router.include_router(webhooks_router)
api_router.include_router(ws_router)
