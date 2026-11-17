from fastapi import FastAPI

from app.api import health

app = FastAPI(
    title="Exin Lab Search API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

app.include_router(health.router, prefix="/api")
