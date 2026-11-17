from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()


@router.get("/health")
def health(response: Response, db: Session = Depends(get_db)):
    try:
        pgvector = db.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar()
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "unreachable"}

    return {"status": "ok", "database": "ok", "pgvector": pgvector}
