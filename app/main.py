from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB engine / Redis client startup + shutdown will hook in here (Phase 1 & 3)
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
