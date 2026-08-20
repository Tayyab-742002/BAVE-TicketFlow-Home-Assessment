from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.openapi import API_DESCRIPTION, TAGS_METADATA
from app.db.redis import redis_client
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.ping()
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=API_DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
)
register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["health"], summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok"}
