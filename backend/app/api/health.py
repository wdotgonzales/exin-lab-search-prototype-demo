from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/health")
def health(response: Response, db: DbSession):
    try:
        pgvector = db.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar()
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "unreachable"}

    return {"status": "ok", "database": "ok", "pgvector": pgvector}
