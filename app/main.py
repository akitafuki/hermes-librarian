"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, APP_TITLE, APP_DESCRIPTION, APP_HOST, APP_PORT, ensure_directories
from app.database import init_db
from app.routes import api, web


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown hooks."""
    ensure_directories()
    init_db()
    yield


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

# Include routers
app.include_router(api.router)
app.include_router(web.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, reload=True)
