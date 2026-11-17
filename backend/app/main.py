from fastapi import FastAPI

from app.api import health

app = FastAPI(title="Exin Lab Search API", version="0.1.0")

app.include_router(health.router, prefix="/api")
